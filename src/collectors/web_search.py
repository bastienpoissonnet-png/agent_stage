"""Collecteur complémentaire via recherche web DuckDuckGo (ddgs) pour contourner les anti-bots."""

import logging
import re
from typing import List, Set
from ddgs import DDGS

from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.web_search")


class WebSearchCollector(BaseJobCollector):
    """Repère les offres de stage indexées sur Welcome to the Jungle via DuckDuckGo."""

    QUERIES = [
        'stage data python Paris site:welcometothejungle.com/fr/companies',
        'stage intelligence artificielle Paris site:welcometothejungle.com/fr/companies',
        'stage informatique Niort OR "La Rochelle" site:welcometothejungle.com/fr/companies',
    ]

    def __init__(self):
        super().__init__(name="Web Search (WTTJ / JobTeaser)")

    @staticmethod
    def _extract_company_from_url(url: str) -> str:
        match = re.search(r"/companies/([^/]+)/jobs/", url)
        if not match:
            return "Entreprise Tech"
        return match.group(1).replace("-", " ").title()

    @staticmethod
    def _infer_location(text: str) -> str:
        text_lower = text.lower()
        for city, label in [
            ("la rochelle", "17 - La Rochelle"),
            ("niort", "79 - Niort"),
            ("la roche-sur-yon", "85 - La Roche-sur-Yon"),
            ("paris", "75 - Paris"),
            ("île-de-france", "Île-de-France"),
            ("ile-de-france", "Île-de-France"),
        ]:
            if city in text_lower:
                return label
        return "France"

    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Recherche via ddgs et ne conserve que les liens directs vers des fiches d'offres."""
        offers: List[JobOffer] = []
        seen_urls: Set[str] = set()

        try:
            with DDGS() as ddgs:
                for query in self.QUERIES:
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
                        location = self._infer_location(f"{raw_title} {snippet} {query}")
                        dept_match = re.match(r"^(\d{2})\s*-", location)
                        dept = dept_match.group(1) if dept_match else None

                        offer_id = JobOffer.generate_id(self.name, title, company, href)
                        offers.append(
                            JobOffer(
                                id=offer_id,
                                title=title,
                                company=company,
                                location=location,
                                department=dept,
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
