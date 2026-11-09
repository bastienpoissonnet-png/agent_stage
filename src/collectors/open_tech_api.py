"""Collecteur d'offres via des APIs ouvertes spécialisées Tech & Data."""

import logging
from typing import List
import requests
from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.open_tech")


class OpenTechApiCollector(BaseJobCollector):
    """Agrégateur d'APIs tech ouvertes (Remotive, RemoteOK, Jobicy) sans clé requise."""

    def __init__(self):
        super().__init__(name="Open Tech APIs")

    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Interroge les flux JSON ouverts pour trouver des stages et postes juniors tech/data."""
        offers: List[JobOffer] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0"
        }

        # 1. Remotive (Data & Dev)
        remotive_endpoints = [
            "https://remotive.com/api/remote-jobs?category=data",
            "https://remotive.com/api/remote-jobs?category=software-dev",
        ]
        for url in remotive_endpoints:
            if len(offers) >= limit:
                break
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    jobs = resp.json().get("jobs", [])
                    for j in jobs:
                        title = j.get("title", "")
                        desc = self.clean_html(j.get("description", ""))
                        job_type = j.get("job_type", "").lower()
                        tags = [t.lower() for t in j.get("tags", [])]

                        # Filtrer sur profil junior, stage, python ou data
                        is_intern_or_junior = any(
                            kw in title.lower() or kw in tags or kw in desc.lower()[:300]
                            for kw in ["intern", "stage", "junior", "entry level", "trainee", "etudiant", "student"]
                        )
                        is_tech_match = any(
                            kw in title.lower() or kw in tags
                            for kw in ["data", "python", "sql", "ai", "machine learning", "backend", "rust", "react"]
                        )

                        if is_tech_match:
                            company = j.get("company_name", "Entreprise Tech")
                            job_url = j.get("url", "")
                            location = j.get("candidate_required_location", "Remote")
                            published = j.get("publication_date", "")[:10]

                            norm_id = JobOffer.generate_id("Remotive", title, company, job_url)
                            offers.append(
                                JobOffer(
                                    id=norm_id,
                                    title=title,
                                    company=company,
                                    location=location,
                                    is_remote=True,
                                    url=job_url,
                                    source="Remotive Tech",
                                    contract_type="Stage / Junior" if is_intern_or_junior else "Contrat Tech",
                                    description=desc,
                                    published_at=published,
                                )
                            )
            except Exception as e:
                logger.debug(f"[Remotive] Erreur : {e}")

        # 2. RemoteOK
        if len(offers) < limit:
            try:
                resp = requests.get("https://remoteok.com/api", headers=headers, timeout=10)
                if resp.status_code == 200:
                    jobs = resp.json()
                    # Le premier élément est légal/disclaimer
                    if isinstance(jobs, list) and len(jobs) > 1:
                        for j in jobs[1:]:
                            if len(offers) >= limit:
                                break
                            title = j.get("position", "")
                            tags = [str(t).lower() for t in j.get("tags", [])]
                            desc = self.clean_html(j.get("description", ""))

                            is_match = any(
                                kw in title.lower() or kw in tags
                                for kw in ["data", "python", "backend", "rust", "ai", "machine learning"]
                            )
                            if is_match:
                                company = j.get("company", "Tech Company")
                                job_url = j.get("url", f"https://remoteok.com/remote-jobs/{j.get('id')}")
                                location = j.get("location", "Remote")
                                published = j.get("date", "")[:10]

                                is_intern = any(
                                    kw in title.lower() or kw in tags
                                    for kw in ["intern", "stage", "junior", "entry level", "student"]
                                )

                                norm_id = JobOffer.generate_id("RemoteOK", title, company, job_url)
                                offers.append(
                                    JobOffer(
                                        id=norm_id,
                                        title=title,
                                        company=company,
                                        location=location,
                                        is_remote=True,
                                        url=job_url,
                                        source="RemoteOK",
                                        contract_type="Stage / Junior" if is_intern else "Remote Tech",
                                        description=desc,
                                        published_at=published,
                                    )
                                )
            except Exception as e:
                logger.debug(f"[RemoteOK] Erreur : {e}")

        # 3. Jobicy
        if len(offers) < limit:
            try:
                resp = requests.get(
                    "https://jobicy.com/api/v2/remote-jobs?count=20&tag=python",
                    headers=headers,
                    timeout=10,
                )
                if resp.status_code == 200:
                    jobs = resp.json().get("jobs", [])
                    for j in jobs:
                        if len(offers) >= limit:
                            break
                        title = j.get("jobTitle", "")
                        company = j.get("companyName", "Tech Company")
                        desc = self.clean_html(j.get("jobDescription", ""))
                        job_url = j.get("url", "")
                        location = j.get("jobGeo", "Remote")
                        published = j.get("pubDate", "")[:10]

                        norm_id = JobOffer.generate_id("Jobicy", title, company, job_url)
                        offers.append(
                            JobOffer(
                                id=norm_id,
                                title=title,
                                company=company,
                                location=location,
                                is_remote=True,
                                url=job_url,
                                source="Jobicy",
                                contract_type="Stage / Remote Tech",
                                description=desc,
                                published_at=published,
                            )
                        )
            except Exception as e:
                logger.debug(f"[Jobicy] Erreur : {e}")

        logger.info(f"[Open Tech APIs] {len(offers)} offres récupérées.")
        return offers
