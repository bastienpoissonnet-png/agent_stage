"""Collecteur d'offres officiel France Travail (v2) avec endpoint OAuth2 officiel."""

import logging
import time
from typing import Dict, List, Optional
import requests
from config.settings import settings
from src.collectors.base import BaseJobCollector
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors.france_travail")


class FranceTravailCollector(BaseJobCollector):
    """Client pour l'API Offres d'emploi v2 de France Travail via entreprise.pole-emploi.fr."""

    # Endpoint OAuth2 historique et officiel toujours actif
    TOKEN_URL = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=/partenaire"
    SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

    def __init__(self):
        super().__init__(name="France Travail")
        self.auth_url = settings.france_travail.auth_url or self.TOKEN_URL
        self.search_url = settings.france_travail.search_url or self.SEARCH_URL
        self.client_id = settings.france_travail.client_id
        self.client_secret = settings.france_travail.client_secret

        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        """Vérifie si les clés d'API ont bien été fournies dans le .env."""
        return settings.france_travail.is_configured

    def _get_access_token(self) -> Optional[str]:
        """Récupère ou réutilise un token OAuth2 valide via le flux client_credentials."""
        if not self.is_configured():
            return None

        if self._token and time.time() < (self._token_expires_at - 60):
            return self._token

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(self.auth_url, data=data, headers=headers, timeout=12)
            if response.status_code == 200:
                json_data = response.json()
                self._token = json_data.get("access_token")
                expires_in = json_data.get("expires_in", 1499)
                self._token_expires_at = time.time() + expires_in
                logger.info("Connexion OAuth2 France Travail réussie via entreprise.pole-emploi.fr.")
                return self._token
            else:
                logger.warning(
                    f"Échec authentification France Travail (HTTP {response.status_code}): {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Erreur de connexion OAuth2 France Travail : {e}")
            return None

    def fetch_offers(self, limit: int = 40) -> List[JobOffer]:
        """Interroge France Travail en ciblant les départements 17, 79, 85, 75 et les stages tech."""
        if not self.is_configured():
            logger.warning(
                "France Travail API ignorée : Renseigne FRANCE_TRAVAIL_CLIENT_ID et FRANCE_TRAVAIL_CLIENT_SECRET dans .env."
            )
            return []

        token = self._get_access_token()
        if not token:
            logger.warning("Impossible d'obtenir un jeton d'accès France Travail.")
            return []

        offers: List[JobOffer] = []
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        target_departments = ["17", "79", "85", "75"]
        seen_ids = set()

        # Requêtes calibrées pour France Travail v2 (natureContrat=FS correspond à Stage / Formation)
        queries: List[Dict[str, str]] = []

        # 1. Par département avec mot-clé explicite stage + domaine
        for dept in target_departments:
            queries.append({"natureContrat": "FS", "departement": dept, "motsCles": "stage informatique"})
            queries.append({"natureContrat": "FS", "departement": dept, "motsCles": "stage data"})
            queries.append({"natureContrat": "FS", "departement": dept, "motsCles": "stage python"})
            queries.append({"departement": dept, "motsCles": "stage developpeur"})
            queries.append({"departement": dept, "motsCles": "stage data engineer"})

        # 2. Requêtes nationales axées stage sur les technologies clés
        queries.extend([
            {"natureContrat": "FS", "motsCles": "stage python"},
            {"natureContrat": "FS", "motsCles": "stage data engineer"},
            {"natureContrat": "FS", "motsCles": "stage intelligence artificielle"},
            {"natureContrat": "FS", "motsCles": "stage machine learning"},
            {"motsCles": "stage BUT informatique"},
            {"motsCles": "stage fin d'etudes informatique"},
        ])

        for q_params in queries:
            if len(offers) >= limit:
                break

            params = {
                "range": "0-29",
                **q_params,
            }

            try:
                response = requests.get(
                    self.search_url,
                    headers=headers,
                    params=params,
                    timeout=15,
                )

                if response.status_code in (200, 206):
                    data = response.json()
                    results = data.get("resultats", [])
                    for item in results:
                        offer_id = item.get("id")
                        if not offer_id or offer_id in seen_ids:
                            continue
                        seen_ids.add(offer_id)

                        location_dict = item.get("lieuTravail", {})
                        city = location_dict.get("libelle", "France")
                        dept = (
                            location_dict.get("codePostal", "")[:2]
                            if location_dict.get("codePostal")
                            else None
                        )

                        title = item.get("intitule", "")
                        company = item.get("entreprise", {}).get("nom", "Confidentiel / Non spécifié")
                        desc = item.get("description", "")
                        url = item.get("origineOffre", {}).get(
                            "urlOrigine",
                            f"https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}",
                        )
                        published = item.get("dateCreation", "")[:10]

                        # Détection télétravail/hybride
                        is_remote = False
                        desc_lower = desc.lower()
                        if "full remote" in desc_lower or "100% télétravail" in desc_lower:
                            is_remote = True

                        norm_id = JobOffer.generate_id(self.name, title, company, url)
                        offers.append(
                            JobOffer(
                                id=norm_id,
                                title=title,
                                company=company,
                                location=city,
                                department=dept,
                                is_remote=is_remote,
                                url=url,
                                source=self.name,
                                contract_type="Stage",
                                description=self.clean_html(desc),
                                published_at=published,
                            )
                        )
                elif response.status_code == 204:
                    logger.debug(f"Aucune offre France Travail pour : {q_params}")
                elif response.status_code == 400:
                    logger.debug(f"Paramètre refusé par l'API France Travail sur {q_params} : {response.text}")
                else:
                    logger.warning(
                        f"API France Travail {response.status_code} sur {q_params} : {response.text}"
                    )
            except Exception as e:
                logger.error(f"Erreur requête France Travail : {e}")

        logger.info(f"[France Travail] {len(offers)} offres récupérées.")
        return offers
