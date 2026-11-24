"""Module de chargement dynamique de la configuration et du profil candidat."""

import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


class SmtpSettings:
    def __init__(self):
        self.host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port: int = int(os.getenv("SMTP_PORT", "587"))
        self.user: Optional[str] = os.getenv("SMTP_USER")
        self.password: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.sender_email: str = os.getenv("SENDER_EMAIL", "")
        self.sender_name: str = os.getenv("SENDER_NAME", "")
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
        self.profile_example_path: Path = self.config_dir / "profile.example.json"
        self.target_companies_path: Path = self.data_dir / "target_companies.csv"
        self.csv_output_path: Path = PROJECT_ROOT / "candidatures.csv"
        self.md_output_path: Path = PROJECT_ROOT / "candidatures.md"
        self.spontaneous_csv_path: Path = PROJECT_ROOT / "suivi_spontanees.csv"

        self.min_score_threshold: int = int(os.getenv("MIN_SCORE_THRESHOLD", "40"))
        self.max_offers_per_source: int = int(os.getenv("MAX_OFFERS_PER_SOURCE", "30"))

        self.smtp = SmtpSettings()
        self.profile: Dict[str, Any] = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        if not self.profile_path.exists():
            if self.profile_example_path.exists():
                shutil.copyfile(self.profile_example_path, self.profile_path)
            else:
                raise FileNotFoundError(f"Fichier de profil introuvable : {self.profile_path}")
        with open(self.profile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def reload(self) -> None:
        """Recharge le .env et profile.json sans redémarrer l'application."""
        load_dotenv(ENV_PATH, override=True)
        self.min_score_threshold = int(os.getenv("MIN_SCORE_THRESHOLD", "40"))
        self.max_offers_per_source = int(os.getenv("MAX_OFFERS_PER_SOURCE", "30"))
        self.smtp = SmtpSettings()
        self.profile = self._load_profile()

    def save_profile(self, data: Dict[str, Any]) -> None:
        """Sauvegarde profile.json et recharge les réglages en mémoire."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.profile = data

    def save_smtp_config(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender_email: str,
        sender_name: str,
    ) -> None:
        """Met à jour les clés SMTP dans .env en préservant les autres variables."""
        lines: List[str] = []
        if ENV_PATH.exists():
            lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

        updates = {
            "SMTP_HOST": host.strip(),
            "SMTP_PORT": str(port),
            "SMTP_USER": user.strip(),
            "SMTP_PASSWORD": password.strip(),
            "SENDER_EMAIL": (sender_email or user).strip(),
            "SENDER_NAME": sender_name.strip(),
        }
        seen = set()
        new_lines: List[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}")
                    seen.add(key)
                    continue
            new_lines.append(line)

        for key, val in updates.items():
            if key not in seen:
                new_lines.append(f"{key}={val}")

        ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        self.reload()

    @property
    def candidate_name(self) -> str:
        return self.profile.get("candidate", {}).get("name", "")

    @property
    def candidate_email(self) -> str:
        return self.profile.get("candidate", {}).get("email", "")

    @property
    def internship_period(self) -> str:
        return self.profile.get("search_criteria", {}).get("internship_period", "")

    @property
    def project_highlight(self) -> str:
        return self.profile.get("candidate", {}).get("project_highlight", "")

    @property
    def cv_path(self) -> Path:
        configured = (self.profile.get("candidate", {}).get("cv_filename") or "").strip()
        candidates: List[Path] = []
        if configured:
            p = Path(configured)
            candidates.append(p if p.is_absolute() else self.project_root / p)
        candidates.extend([
            self.data_dir / "cv.pdf",
            self.project_root / "CV_Bastien_Poissonnet.pdf",
            self.project_root / "cv.pdf",
        ])
        for c in candidates:
            if c.exists():
                return c
        return candidates[0]

    @property
    def target_roles(self) -> List[str]:
        return self.profile.get("search_criteria", {}).get("target_roles", [])

    @property
    def search_keywords(self) -> List[str]:
        kws = self.profile.get("search_criteria", {}).get("search_keywords")
        if kws:
            return kws
        return [s for s in self.core_skills[:5] if s] or ["stage"]

    @property
    def target_locations(self) -> List[str]:
        return self.profile.get("search_criteria", {}).get("target_locations", [])

    @property
    def target_departments(self) -> List[str]:
        return [str(d).strip() for d in self.profile.get("search_criteria", {}).get("target_departments", []) if str(d).strip()]

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

    @property
    def exclude_alternance(self) -> bool:
        return self.profile.get("search_criteria", {}).get("exclude_alternance", True)

    @property
    def exclude_non_tech(self) -> bool:
        return self.profile.get("search_criteria", {}).get("exclude_non_tech", True)

    @property
    def excluded_title_keywords(self) -> List[str]:
        return [str(k).strip().lower() for k in self.profile.get("search_criteria", {}).get("excluded_title_keywords", []) if str(k).strip()]

    @property
    def bonus_sector_keywords(self) -> List[str]:
        return [str(k).strip().lower() for k in self.profile.get("search_criteria", {}).get("bonus_sector_keywords", []) if str(k).strip()]


settings = Settings()
