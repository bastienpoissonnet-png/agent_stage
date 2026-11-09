"""Module de chargement de la configuration et du profil candidat."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Charger les variables du fichier .env s'il existe
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class FranceTravailSettings:
    def __init__(self):
        self.client_id: Optional[str] = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
        self.client_secret: Optional[str] = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
        self.auth_url: str = (
            "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=/partenaire"
        )
        self.search_url: str = (
            "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
        )

    @property
    def is_configured(self) -> bool:
        return bool(
            self.client_id
            and self.client_secret
            and self.client_id != "votre_client_id_ici"
            and self.client_secret != "votre_client_secret_ici"
        )


class SmtpSettings:
    def __init__(self):
        self.host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port: int = int(os.getenv("SMTP_PORT", "587"))
        self.user: Optional[str] = os.getenv("SMTP_USER")
        self.password: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.sender_email: str = os.getenv("SENDER_EMAIL", "bastien.poissonnet@gmail.com")
        self.sender_name: str = os.getenv("SENDER_NAME", "Bastien Poissonnet")
        self.delay_min: int = int(os.getenv("SMTP_DELAY_MIN", "5"))
        self.delay_max: int = int(os.getenv("SMTP_DELAY_MAX", "12"))

    @property
    def is_configured(self) -> bool:
        return bool(
            self.user
            and self.password
            and self.password != "votre_mot_de_passe_application_google"
        )


class Settings:
    def __init__(self):
        self.project_root: Path = PROJECT_ROOT
        self.config_dir: Path = PROJECT_ROOT / "config"
        self.data_dir: Path = PROJECT_ROOT / "data"
        self.profile_path: Path = self.config_dir / "profile.json"
        self.target_companies_path: Path = self.data_dir / "target_companies.csv"
        self.csv_output_path: Path = PROJECT_ROOT / "candidatures.csv"
        self.md_output_path: Path = PROJECT_ROOT / "candidatures.md"
        self.spontaneous_csv_path: Path = PROJECT_ROOT / "suivi_spontanees.csv"

        self.min_score_threshold: int = int(os.getenv("MIN_SCORE_THRESHOLD", "40"))
        self.max_offers_per_source: int = int(os.getenv("MAX_OFFERS_PER_SOURCE", "30"))

        self.france_travail = FranceTravailSettings()
        self.smtp = SmtpSettings()
        self.profile: Dict[str, Any] = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        if not self.profile_path.exists():
            raise FileNotFoundError(f"Fichier de profil introuvable : {self.profile_path}")
        with open(self.profile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def candidate_name(self) -> str:
        return self.profile.get("candidate", {}).get("name", "Bastien Poissonnet")

    @property
    def target_roles(self) -> List[str]:
        return self.profile.get("search_criteria", {}).get("target_roles", [])

    @property
    def target_locations(self) -> List[str]:
        return self.profile.get("search_criteria", {}).get("target_locations", [])

    @property
    def target_departments(self) -> List[str]:
        return self.profile.get("search_criteria", {}).get("target_departments", ["17", "79", "85", "75"])

    @property
    def core_skills(self) -> List[str]:
        return self.profile.get("skills", {}).get("core", [])

    @property
    def secondary_skills(self) -> List[str]:
        return self.profile.get("skills", {}).get("secondary", [])

    @property
    def allow_remote(self) -> bool:
        return self.profile.get("search_criteria", {}).get("allow_remote", False)

    @property
    def disallow_full_remote(self) -> bool:
        return self.profile.get("search_criteria", {}).get("disallow_full_remote", True)


settings = Settings()
