"""Modèles de données pour la campagne de candidatures spontanées."""

from typing import Optional
from pydantic import BaseModel


class TargetCompany(BaseModel):
    """Représentation d'une entreprise cible issue du sourcing local."""

    name: str
    city: str
    department: str
    sector: str
    website: str
    contact_email: str
    context_note: str = ""


class SpontaneousApplication(BaseModel):
    """Représentation d'un email de candidature spontanée préparé ou envoyé."""

    company_name: str
    city: str
    contact_email: str
    subject: str
    body: str
    sent_at: Optional[str] = None
    status: str = "Prêt à envoyer"
    follow_up_date: Optional[str] = None
    notes: str = ""
    letter_path: Optional[str] = None

