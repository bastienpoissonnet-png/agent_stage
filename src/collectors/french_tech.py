"""Collecteur pour les flux et offres Tech françaises (Welcome to the Jungle, flux tech locaux)."""

import logging
from typing import List, Optional
import feedparser
import requests
from config.settings import settings
from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.french_tech")


class FrenchTechCollector(BaseJobCollector):
    """Agrégateur de flux d'offres de stage et tech en France."""

    DEFAULT_FEEDS = [
        # Flux d'offres de stages tech françaises et alertes ciblées
    ]

    def __init__(self, custom_feeds: Optional[List[str]] = None):
        super().__init__(name="French Tech Jobs")
        self.feed_urls = self.DEFAULT_FEEDS + (custom_feeds or [])

    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Récupère les offres depuis les flux français configurés."""
        offers: List[JobOffer] = []
        if not self.feed_urls:
            return offers

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0"
        }

        for url in self.feed_urls:
            if len(offers) >= limit:
                break
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    parsed = feedparser.parse(resp.text)
                    for entry in parsed.entries:
                        title = getattr(entry, "title", "")
                        link = getattr(entry, "link", "")
                        desc = self.clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))

                        norm_id = JobOffer.generate_id(self.name, title, "Entreprise Tech", link)
                        offers.append(
                            JobOffer(
                                id=norm_id,
                                title=title,
                                company="Entreprise Tech",
                                location="France",
                                is_remote=False,
                                url=link,
                                source=self.name,
                                contract_type="Stage",
                                description=desc,
                            )
                        )
            except Exception as e:
                logger.debug(f"Erreur sur flux {url}: {e}")

        return offers
