"""Module de collecte des offres d'emploi et de stage."""
from .base import BaseJobCollector
from .france_travail import FranceTravailCollector
from .wttj import WelcomeToTheJungleCollector
from .french_tech import FrenchTechCollector

__all__ = [
    "BaseJobCollector",
    "FranceTravailCollector",
    "WelcomeToTheJungleCollector",
    "FrenchTechCollector",
]
