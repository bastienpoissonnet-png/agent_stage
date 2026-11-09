"""Classe abstraite de base pour les collecteurs d'offres."""

import abc
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models import JobOffer

logger = logging.getLogger("stage_agent.collectors")


class BaseJobCollector(abc.ABC):
    """Interface générique pour toute source d'offres de stage."""

    def __init__(self, name: str):
        self.name = name

    @abc.abstractmethod
    def fetch_offers(self, limit: int = 30) -> List[JobOffer]:
        """Récupère et normalise une liste d'offres de stage."""
        pass

    @staticmethod
    def clean_html(raw_html: Optional[str]) -> str:
        """Supprime les balises HTML et nettoie les espaces."""
        if not raw_html:
            return ""
        try:
            soup = BeautifulSoup(raw_html, "html.parser")
            text = soup.get_text(separator=" ")
            return " ".join(text.split())
        except Exception:
            return raw_html.strip()
