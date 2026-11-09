"""Modèles de données du pipeline de recherche de stage."""

import hashlib
from typing import List, Optional
from pydantic import BaseModel, Field


class JobOffer(BaseModel):
    """Représentation standardisée d'une offre de stage."""

    id: str
    title: str
    company: str
    location: str = "Non spécifié"
    department: Optional[str] = None
    is_remote: bool = False
    url: str
    source: str
    contract_type: str = "Stage"
    description: str = ""
    published_at: str = ""
    detected_skills: List[str] = Field(default_factory=list)
    score: int = 0
    match_reasons: List[str] = Field(default_factory=list)
    status: str = "À contacter"
    personalized_pitch: str = ""
    letter_path: str = ""

    @classmethod
    def generate_id(cls, source: str, title: str, company: str, url: str) -> str:
        """Génère un identifiant déterministe pour éviter les doublons."""
        raw = f"{source}:{company.strip().lower()}:{title.strip().lower()}:{url.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def to_csv_dict(self) -> dict:
        """Sérialise pour le tableau CSV de suivi."""
        return {
            "ID": self.id,
            "Date": self.published_at,
            "Entreprise": self.company,
            "Intitulé": self.title,
            "Localisation": self.location,
            "Télétravail": "Oui" if self.is_remote else "Non",
            "Score": self.score,
            "Statut": self.status,
            "Source": self.source,
            "Lien": self.url,
            "Compétences": ", ".join(self.detected_skills),
            "Accroche": self.personalized_pitch.replace("\n", " "),
            "Lettre": self.letter_path,
        }

