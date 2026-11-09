"""Collecteur de flux RSS tech et alertes personnalisées."""

import logging
from typing import List, Optional
import feedparser
import requests
from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.rss")


class TechRssCollector(BaseJobCollector):
    """Collecte d'offres via des flux RSS (WeWorkRemotely, Google Alerts RSS, etc.)."""

    DEFAULT_FEEDS = [
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    ]

    def __init__(self, custom_feeds: Optional[List[str]] = None):
        super().__init__(name="Flux RSS Tech")
        self.feed_urls = self.DEFAULT_FEEDS + (custom_feeds or [])

    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Télécharge et extrait les offres depuis les flux RSS configurés."""
        offers: List[JobOffer] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0"
        }

        for feed_url in self.feed_urls:
            if len(offers) >= limit:
                break
            try:
                # Récupération HTTP sécurisée avec timeout
                resp = requests.get(feed_url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    continue

                parsed = feedparser.parse(resp.text)
                for entry in parsed.entries:
                    if len(offers) >= limit:
                        break

                    title = getattr(entry, "title", "")
                    link = getattr(entry, "link", "")
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                    clean_summary = self.clean_html(summary)
                    published = getattr(entry, "published", "")[:10]

                    # Détection entreprise dans le titre ou les balises
                    company = "Entreprise Tech"
                    if ":" in title:
                        parts = title.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()
                    elif "-" in title:
                        parts = title.split("-", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()

                    norm_id = JobOffer.generate_id("RSS", title, company, link)
                    offers.append(
                        JobOffer(
                            id=norm_id,
                            title=title,
                            company=company,
                            location="Remote / À préciser",
                            is_remote=True,
                            url=link,
                            source=f"RSS ({parsed.feed.get('title', 'Tech')})",
                            contract_type="Stage / Remote",
                            description=clean_summary,
                            published_at=published,
                        )
                    )
            except Exception as e:
                logger.debug(f"[RSS] Erreur sur le flux {feed_url}: {e}")

        logger.info(f"[RSS] {len(offers)} offres récupérées.")
        return offers
