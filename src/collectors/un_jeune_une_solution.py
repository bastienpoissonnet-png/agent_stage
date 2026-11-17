"""Collecteur d'offres via le portail officiel 1jeune1solution.gouv.fr (__NEXT_DATA__)."""

import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup
import requests

from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.un_jeune_une_solution")


class UnJeuneUneSolutionCollector(BaseJobCollector):
    """Collecte les stages depuis les données JSON embarquées de 1jeune1solution.gouv.fr."""

    BASE_URL = "https://www.1jeune1solution.gouv.fr/stages"

    DEPT_MAP: Dict[str, str] = {
        "charente-maritime": "17",
        "la rochelle": "17",
        "deux-sèvres": "79",
        "deux-sevres": "79",
        "niort": "79",
        "vendée": "85",
        "vendee": "85",
        "la roche-sur-yon": "85",
        "paris": "75",
        "hauts-de-seine": "92",
        "seine-saint-denis": "93",
        "val-de-marne": "94",
    }

    QUERIES: List[str] = [
        "informatique niort",
        "data niort",
        "informatique la rochelle",
        "data la rochelle",
        "informatique vendee",
        "data python paris",
        "data engineer paris",
        "intelligence artificielle paris",
    ]

    def __init__(self):
        super().__init__(name="1jeune1solution")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9",
        }

    def _match_location(self, loc_list: Optional[List[str]]) -> Tuple[bool, Optional[str], str]:
        """Vérifie si localisationFiltree correspond aux zones cibles."""
        if not loc_list:
            return False, None, ""
        cleaned = [str(part).strip() for part in loc_list if part]
        joined = " ".join(cleaned).lower()

        for key, dept in self.DEPT_MAP.items():
            if key in joined:
                city = cleaned[0] if cleaned else key.title()
                return True, dept, city

        if "île-de-france" in joined or "ile-de-france" in joined:
            city = cleaned[0] if cleaned else "Île-de-France"
            return True, None, city

        return False, None, ""

    def _fetch_detail(self, session: requests.Session, slug: str, fallback_city: str, fallback_dept: Optional[str]) -> Optional[JobOffer]:
        """Charge le détail d'une offre depuis /stages/<slug>."""
        offer_url = f"{self.BASE_URL}/{slug}"
        try:
            resp = session.get(offer_url, timeout=8)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            nd_script = soup.find("script", id="__NEXT_DATA__")
            if not nd_script or not nd_script.string:
                return None

            payload = json.loads(nd_script.string)
            offre = payload.get("props", {}).get("pageProps", {}).get("offreDeStage") or {}
            if not offre:
                return None

            title = str(offre.get("titre") or "").strip()
            if not title:
                return None

            emp = offre.get("employeur") or {}
            company = (emp.get("nom") if isinstance(emp, dict) else None) or "Entreprise non précisée"

            loc = offre.get("localisation") or {}
            ville = (loc.get("ville") if isinstance(loc, dict) else None) or fallback_city or "France"
            cp = str((loc.get("codePostal") if isinstance(loc, dict) else None) or "")
            dept = cp[:2] if len(cp) >= 2 and cp[:2].isdigit() else fallback_dept
            location = f"{dept} - {ville}" if dept else ville

            description = self.clean_html(offre.get("description", ""))
            published_at = str(offre.get("dateDeDebutMin") or "")[:10]

            desc_lower = description.lower()
            is_remote = "full remote" in desc_lower or "100% télétravail" in desc_lower

            offer_id = JobOffer.generate_id(self.name, title, company, offer_url)
            return JobOffer(
                id=offer_id,
                title=title,
                company=company,
                location=location,
                department=dept,
                is_remote=is_remote,
                url=offer_url,
                source=self.name,
                contract_type="Stage",
                description=description,
                published_at=published_at,
            )
        except Exception as e:
            logger.debug(f"[1jeune1solution] Erreur fiche {slug}: {e}")
            return None

    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Interroge 1jeune1solution.gouv.fr et extrait les stages localisés dans les zones cibles."""
        offers: List[JobOffer] = []
        seen_slugs: Set[str] = set()
        session = requests.Session()
        session.headers.update(self.headers)

        for mot_cle in self.QUERIES:
            if len(offers) >= limit:
                break
            try:
                resp = session.get(self.BASE_URL, params={"motCle": mot_cle}, timeout=10)
                if resp.status_code != 200:
                    logger.debug(f"[1jeune1solution] HTTP {resp.status_code} sur '{mot_cle}'")
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                nd_script = soup.find("script", id="__NEXT_DATA__")
                if not nd_script or not nd_script.string:
                    continue

                data = json.loads(nd_script.string)
                items = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("resultats", {})
                    .get("resultats", [])
                )

                for item in items:
                    if len(offers) >= limit:
                        break
                    slug = item.get("slug")
                    if not slug or slug in seen_slugs:
                        continue

                    matched, dept, city = self._match_location(item.get("localisationFiltree"))
                    if not matched:
                        continue

                    seen_slugs.add(slug)
                    title_preview = str(item.get("titre") or "").lower()
                    if any(w in title_preview for w in ("alternance", "apprenti", "apprentissage")) and "stage" not in title_preview:
                        continue

                    offer = self._fetch_detail(session, slug, city, dept)
                    if offer:
                        offers.append(offer)
            except Exception as e:
                logger.warning(f"[1jeune1solution] Erreur requête '{mot_cle}': {e}")

        logger.info(f"[1jeune1solution] {len(offers)} offres de stage récupérées.")
        return offers
