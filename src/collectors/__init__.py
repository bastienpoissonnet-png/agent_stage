"""Module de collecte des offres de stage."""
from .base import BaseJobCollector
from .hellowork import HelloWorkCollector
from .un_jeune_une_solution import UnJeuneUneSolutionCollector
from .web_search import WebSearchCollector

__all__ = [
    "BaseJobCollector",
    "HelloWorkCollector",
    "UnJeuneUneSolutionCollector",
    "WebSearchCollector",
]
