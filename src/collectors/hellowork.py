"""Collecteur d'offres de stage via HelloWork (HTML + JSON-LD JobPosting)."""

import json
import logging
import re
from typing import List, Optional, Set, Tuple
from bs4 import BeautifulSoup
import requests

from config.settings import settings
from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.hellowork")


class HelloWorkCollector(BaseJobCollector):
    """Collecte les offres de stage sur HelloWork selon les mots-clés et zones du profil."""

    BASE_URL = "https://www.hellowork.com"
    SEARCH_URL = f"{BASE_URL}/fr-fr/emploi/recherche.html"

    def __init__(self):
        super().__init__(name="HelloWork")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9",
        }

    def _build_searches(self) -> List[Tuple[str, str]]:
        """Construit les couples (mot-clé, lieu) depuis settings en mettant Paris/IDF en dernier."""
        keywords = settings.search_keywords[:4] or ["stage"]
        raw_locs = [loc.strip() for loc in settings.target_locations if loc.strip()]
        if not raw_locs:
            raw_locs = ["France"]

        # Trier pour éviter que Paris/Île-de-France ne sature la limite avant les villes locales
        local_locs = [l for l in raw_locs if "paris" not in l.lower() and "île-de-france" not in l.lower() and "ile-de-france" not in l.lower()]
        paris_locs = [l for l in raw_locs if l not in local_locs]
        ordered_locs = (local_locs + paris_locs)[:5]

        searches: List[Tuple[str, str]] = []
        for loc in ordered_locs:
            for kw in keywords[:3]:
                searches.append((kw, loc))
                if len(searches) >= 14:
                    return searches
        return searches

    def _should_skip_card(self, link_text: str, card_text: str, target_depts: Set[str]) -> bool:
        """Écarte rapidement les cartes hors département cible ou hors sujet."""
        title_lower = link_text.lower()
        if any(bad in title_lower for bad in ("stage 3eme", "stage 3e", "stage de 3ème", "découverte")):
            return True

        if settings.exclude_alternance:
            has_alternance = any(w in title_lower for w in ("alternance", "apprenti", "apprentissage"))
            if has_alternance and "stage" not in title_lower:
                return True

        if target_depts:
            dept_match = re.search(r"-\s*(\d{2,3})\b", card_text)
            if dept_match and dept_match.group(1) not in target_depts:
                return True

        return False

    def _parse_detail(self, job_url: str, fallback_title: str) -> Optional[JobOffer]:
        """Récupère la fiche complète depuis le bloc JSON-LD JobPosting."""
        try:
            resp = requests.get(job_url, headers=self.headers, timeout=8)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            posting = None
            for script in soup.find_all("script", type="application/ld+json"):
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                except json.JSONDecodeError:
                    continue
                if isinstance(data, list):
                    data = next((d for d in data if isinstance(d, dict) and d.get("@type") == "JobPosting"), None)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    posting = data
                    break

            if not posting:
                return None

            title = (posting.get("title") or fallback_title).strip()
            org = posting.get("hiringOrganization") or {}
            company = (org.get("name") if isinstance(org, dict) else None) or "Entreprise non précisée"

            job_loc = posting.get("jobLocation") or {}
            if isinstance(job_loc, list):
                job_loc = job_loc[0] if job_loc else {}
            address = job_loc.get("address") if isinstance(job_loc, dict) else {}
            if not isinstance(address, dict):
                address = {}

            city = address.get("addressLocality") or "France"
            postal_code = str(address.get("postalCode") or "")
            dept = postal_code[:2] if len(postal_code) >= 2 and postal_code[:2].isdigit() else None
            location = f"{dept} - {city}" if dept else city

            description = self.clean_html(posting.get("description", ""))
            published_at = str(posting.get("datePosted", ""))[:10]

            desc_lower = description.lower()
            is_remote = (
                posting.get("jobLocationType") == "TELECOMMUTE"
                or "full remote" in desc_lower
                or "100% télétravail" in desc_lower
            )

            offer_id = JobOffer.generate_id(self.name, title, company, job_url)
            return JobOffer(
                id=offer_id,
                title=title,
                company=company,
                location=location,
                department=dept,
                is_remote=is_remote,
                url=job_url,
                source=self.name,
                contract_type="Stage",
                description=description,
                published_at=published_at,
            )
        except Exception as e:
            logger.debug(f"[HelloWork] Erreur détail {job_url}: {e}")
            return None

    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Parcourt les recherches HelloWork et extrait les offres de stage qualifiées."""
        offers: List[JobOffer] = []
        seen_paths: Set[str] = set()
        target_depts = set(settings.target_departments)
        searches = self._build_searches()

        session = requests.Session()
        session.headers.update(self.headers)

        for keyword, location in searches:
            if len(offers) >= limit:
                break
            try:
                resp = session.get(
                    self.SEARCH_URL,
                    params={"k": keyword, "c": "Stage", "l": location},
                    timeout=10,
                )
                if resp.status_code != 200:
                    logger.debug(f"[HelloWork] HTTP {resp.status_code} pour {keyword}/{location}")
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                for link in soup.find_all("a", href=re.compile(r"/fr-fr/emplois/\d+\.html")):
                    if len(offers) >= limit:
                        break
                    rel_path = link["href"].split("?")[0]
                    if rel_path in seen_paths:
                        continue
                    seen_paths.add(rel_path)

                    li = link.find_parent("li")
                    card_text = li.get_text(" | ", strip=True) if li else link.get_text(" ", strip=True)
                    link_text = link.get_text(" ", strip=True)

                    if target_depts and "résultats proches" in card_text.lower():
                        dept_match = re.search(r"-\s*(\d{2,3})\b", card_text)
                        if not dept_match or dept_match.group(1) not in target_depts:
                            continue

                    if self._should_skip_card(link_text, card_text, target_depts):
                        continue

                    full_url = f"{self.BASE_URL}{rel_path}"
                    offer = self._parse_detail(full_url, link_text)
                    if offer:
                        offers.append(offer)
            except Exception as e:
                logger.warning(f"[HelloWork] Erreur recherche ({keyword}, {location}): {e}")

        logger.info(f"[HelloWork] {len(offers)} offres de stage récupérées.")
        return offers
