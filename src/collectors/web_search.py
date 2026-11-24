"""Collecteur complémentaire via recherche web DuckDuckGo (ddgs) pour contourner les anti-bots."""

import logging
import re
from typing import List, Set
from ddgs import DDGS

from config.settings import settings
from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.web_search")


class WebSearchCollector(BaseJobCollector):
    """Repère les offres de stage indexées sur Welcome to the Jungle via DuckDuckGo."""

    def __init__(self):
        super().__init__(name="Web Search (WTTJ / JobTeaser)")

    @staticmethod
    def _build_queries() -> List[str]:
        kws = settings.search_keywords[:2] or ["stage"]
        locs = [l.strip() for l in settings.target_locations if l.strip()][:3]
        queries: List[str] = []
        if locs:
            loc_expr = " OR ".join(f'"{l}"' for l in locs)
            for kw in kws:
                queries.append(f'stage {kw} {loc_expr} site:welcometothejungle.com/fr/companies')
        else:
            for kw in kws:
                queries.append(f'stage {kw} site:welcometothejungle.com/fr/companies')
        return queries

    @staticmethod
    def _extract_company_from_url(url: str) -> str:
        match = re.search(r"/companies/([^/]+)/jobs/", url)
        if not match:
            return "Entreprise"
        return match.group(1).replace("-", " ").title()

    @staticmethod
    def _infer_location(text: str) -> str:
        text_lower = text.lower()
        for loc in settings.target_locations:
            if loc.strip() and loc.strip().lower() in text_lower:
                return loc.strip()
        return "France"

    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Recherche via ddgs et ne conserve que les liens directs vers des fiches d'offres."""
        offers: List[JobOffer] = []
        seen_urls: Set[str] = set()

        try:
            with DDGS() as ddgs:
                for query in self._build_queries():
                    if len(offers) >= limit:
                        break
                    try:
                        results = list(ddgs.text(query, region="fr-fr", max_results=8))
                    except Exception as e:
                        logger.debug(f"[WebSearch] Requête '{query}' en erreur : {e}")
                        continue

                    for item in results:
                        if len(offers) >= limit:
                            break
                        href = str(item.get("href") or "").strip()
                        if "/companies/" not in href or "/jobs/" not in href:
                            continue
                        if href in seen_urls:
                            continue
                        seen_urls.add(href)

                        raw_title = str(item.get("title") or "").strip()
                        title = re.sub(r"\s*[-–|]\s*Welcome to the Jungle.*$", "", raw_title, flags=re.I).strip()
                        snippet = self.clean_html(item.get("body") or "")
                        company = self._extract_company_from_url(href)
                        location = self._infer_location(f"{raw_title} {snippet}")

                        offer_id = JobOffer.generate_id(self.name, title, company, href)
                        offers.append(
                            JobOffer(
                                id=offer_id,
                                title=title,
                                company=company,
                                location=location,
                                is_remote="full remote" in snippet.lower() or "100% remote" in snippet.lower(),
                                url=href,
                                source=self.name,
                                contract_type="Stage",
                                description=snippet,
                            )
                        )
        except Exception as e:
            logger.warning(f"[WebSearch] Erreur globale DDGS : {e}")

        logger.info(f"[WebSearch] {len(offers)} fiches d'offres trouvées.")
        return offers
