"""Suivi et historique des candidatures spontanées dans suivi_spontanees.csv."""

import csv
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Dict, List
from config.settings import settings
from src.spontaneous.models import SpontaneousApplication

logger = logging.getLogger("stage_agent.spontaneous.tracker")


class SpontaneousTracker:
    """Gestionnaire de persistance et de relance à J+7 pour les candidatures spontanées."""

    FIELDNAMES = [
        "Entreprise",
        "Ville",
        "Email",
        "Date_Envoi",
        "Statut",
        "Date_Relance_Prevue",
        "Objet",
        "Commentaires",
    ]

    def __init__(self, file_path: Path = settings.spontaneous_csv_path):
        self.file_path = file_path

    def load_existing(self) -> Dict[str, dict]:
        """Charge l'historique existant pour préserver les statuts et relances modifiés manuellement."""
        existing = {}
        if not self.file_path.exists():
            return existing

        try:
            with open(self.file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = row.get("Entreprise", "").strip().lower()
                    if key:
                        existing[key] = row
        except Exception as e:
            logger.warning(f"Erreur lecture de {self.file_path.name} : {e}")

        return existing

    def record_applications(self, apps: List[SpontaneousApplication], mark_as_sent: bool = False) -> int:
        """Enregistre les candidatures avec calcul automatique de la relance à J+7."""
        existing = self.load_existing()
        now = datetime.now()
        now_str = now.strftime("%d/%m/%Y")
        follow_up_str = (now + timedelta(days=7)).strftime("%d/%m/%Y")
        new_count = 0

        for app in apps:
            key = app.company_name.strip().lower()
            current_status = "Envoyé" if mark_as_sent else "Prêt à envoyer (Dry-Run)"

            if key in existing:
                # Préserver le statut manuel si déjà modifié
                manual_status = existing[key].get("Statut")
                if manual_status and manual_status not in ("Prêt à envoyer (Dry-Run)", "À contacter"):
                    current_status = manual_status
                sent_date = existing[key].get("Date_Envoi") or (now_str if mark_as_sent else "Non envoyé")
                follow_up = existing[key].get("Date_Relance_Prevue") or (follow_up_str if mark_as_sent else "À planifier")
            else:
                new_count += 1
                sent_date = now_str if mark_as_sent else "Non envoyé"
                follow_up = follow_up_str if mark_as_sent else "À planifier"

            row = {
                "Entreprise": app.company_name,
                "Ville": app.city,
                "Email": app.contact_email,
                "Date_Envoi": sent_date,
                "Statut": current_status,
                "Date_Relance_Prevue": follow_up,
                "Objet": app.subject,
                "Commentaires": app.notes,
            }
            existing[key] = row

        sorted_rows = sorted(existing.values(), key=lambda r: (r.get("Date_Envoi", ""), r.get("Entreprise", "")))

        try:
            with open(self.file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(sorted_rows)

            logger.info(
                f"[Suivi Spontanées] {len(sorted_rows)} entreprises suivies ({new_count} nouvelles) dans {self.file_path.name}."
            )
            return new_count
        except Exception as e:
            logger.error(f"Erreur écriture dans {self.file_path.name} : {e}")
            return 0
