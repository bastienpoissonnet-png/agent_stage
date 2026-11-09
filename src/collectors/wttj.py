"""Collecteur pour Welcome to the Jungle (WTTJ)."""

import logging
from typing import List
import requests
from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.wttj")


class WelcomeToTheJungleCollector(BaseJobCollector):
    """Collecteur pour Welcome to the Jungle via API de recherche publique Algolia / HTTP."""

    def __init__(self):
        super().__init__(name="Welcome to the Jungle")
        # Identifiants de l'index de recherche public de WTTJ
        self.algolia_app_id = "CSEKHVMS53"
        self.algolia_url = f"https://{self.algolia_app_id.lower()}-dsn.algolia.net/1/indexes/wttj_jobs_production/query"

    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Tente de récupérer les stages Data / Informatique sur WTTJ."""
        offers: List[JobOffer] = []
        queries = ["stage data", "stage python", "stage intelligence artificielle", "stage developpeur"]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        # Tentative via l'API de recherche
        for q in queries:
            if len(offers) >= limit:
                break
            try:
                # WTTJ API search endpoint
                url = f"https://api.welcometothejungle.com/api/v1/jobs?query={requests.utils.quote(q)}&refinementList%5Bcontract_type%5D%5B%5D=internship"
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = data.get("jobs", []) or data.get("hits", [])
                    for j in jobs:
                        title = j.get("name") or j.get("title", "")
                        org = j.get("organization", {})
                        company = org.get("name", "Entreprise Tech")
                        city = j.get("office", {}).get("city", "France")
                        slug = j.get("slug", "")
                        org_slug = org.get("slug", "")
                        job_url = f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{slug}" if slug else "https://www.welcometothejungle.com"
                        desc = self.clean_html(j.get("description", ""))

                        norm_id = JobOffer.generate_id(self.name, title, company, job_url)
                        offers.append(
                            JobOffer(
                                id=norm_id,
                                title=title,
                                company=company,
                                location=city,
                                is_remote=j.get("remote", False) or "remote" in desc.lower(),
                                url=job_url,
                                source=self.name,
                                contract_type="Stage",
                                description=desc,
                                published_at=j.get("published_at", "")[:10],
                            )
                        )
                else:
                    logger.debug(
                        f"[WTTJ] Requête '{q}' non accessible directement ({resp.status_code}) en raison des protections anti-bot (Cloudflare/DataDome)."
                    )
            except Exception as e:
                logger.debug(f"[WTTJ] Exception lors de la requête : {e}")

        if not offers:
            logger.info(
                "[WTTJ] Welcome to the Jungle utilise des protections anti-bot (DataDome). "
                "Le flux France Travail & les flux Tech ouverts prennent automatiquement le relais."
            )
        else:
            logger.info(f"[WTTJ] {len(offers)} offres récupérées.")

        return offers
