"""Suivi et historique des candidatures spontanées dans suivi_spontanees.csv."""

import csv
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Dict, List, Optional
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
    ADVANCED_STATUSES = {"Envoyé", "Relancé", "Réponse reçue", "Entretien", "Refusé"}
    UNSET_DATES = {"", "Non envoyé", "À planifier", None}

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

    def _write_rows(self, existing: Dict[str, dict]) -> bool:
        sorted_rows = sorted(
            existing.values(),
            key=lambda r: (r.get("Date_Envoi", ""), r.get("Entreprise", "")),
        )
        try:
            with open(self.file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(sorted_rows)
            return True
        except Exception as e:
            logger.error(f"Erreur écriture dans {self.file_path.name} : {e}")
            return False

    def record_applications(self, apps: List[SpontaneousApplication], mark_as_sent: bool = False) -> int:
        """Enregistre les candidatures avec calcul automatique de la relance à J+7."""
        existing = self.load_existing()
        now = datetime.now()
        now_str = now.strftime("%d/%m/%Y")
        follow_up_str = (now + timedelta(days=7)).strftime("%d/%m/%Y")
        new_count = 0

        for app in apps:
            key = app.company_name.strip().lower()
            if key in existing:
                old_row = existing[key]
                old_status = (old_row.get("Statut") or "").strip()
                old_sent = old_row.get("Date_Envoi", "")
                old_follow = old_row.get("Date_Relance_Prevue", "")

                if mark_as_sent and old_status in ("", "Prêt à envoyer (Dry-Run)", "À contacter"):
                    current_status = "Envoyé"
                    sent_date = now_str
                    follow_up = follow_up_str
                elif old_status in self.ADVANCED_STATUSES or (
                    old_status and old_status not in ("Prêt à envoyer (Dry-Run)", "À contacter")
                ):
                    current_status = old_status
                    sent_date = old_sent
                    follow_up = old_follow
                else:
                    current_status = "Prêt à envoyer (Dry-Run)"
                    sent_date = old_sent if old_sent not in self.UNSET_DATES else "Non envoyé"
                    follow_up = old_follow if old_follow not in self.UNSET_DATES else "À planifier"
            else:
                new_count += 1
                current_status = "Envoyé" if mark_as_sent else "Prêt à envoyer (Dry-Run)"
                sent_date = now_str if mark_as_sent else "Non envoyé"
                follow_up = follow_up_str if mark_as_sent else "À planifier"

            existing[key] = {
                "Entreprise": app.company_name,
                "Ville": app.city,
                "Email": app.contact_email,
                "Date_Envoi": sent_date,
                "Statut": current_status,
                "Date_Relance_Prevue": follow_up,
                "Objet": app.subject,
                "Commentaires": app.notes,
            }

        if self._write_rows(existing):
            logger.info(
                f"[Suivi Spontanées] {len(existing)} entreprises suivies ({new_count} nouvelles) dans {self.file_path.name}."
            )
            return new_count
        return 0

    def get_due_followups(self, reference_date: Optional[datetime] = None) -> List[dict]:
        """Retourne les candidatures au statut 'Envoyé' dont la relance J+7 est arrivée à échéance."""
        today = (reference_date or datetime.now()).date()
        due: List[dict] = []
        for row in self.load_existing().values():
            if (row.get("Statut") or "").strip() != "Envoyé":
                continue
            raw_date = (row.get("Date_Relance_Prevue") or "").strip()
            try:
                due_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
            except ValueError:
                continue
            if due_date <= today:
                due.append(row)

        due.sort(key=lambda r: datetime.strptime(r["Date_Relance_Prevue"].strip(), "%d/%m/%Y").date())
        return due

    def mark_followed_up(self, company_names: List[str]) -> int:
        """Passe les entreprises relancées au statut 'Relancé' avec la date du jour."""
        existing = self.load_existing()
        today_str = datetime.now().strftime("%d/%m/%Y")
        updated = 0
        for name in company_names:
            key = name.strip().lower()
            if key in existing:
                existing[key]["Statut"] = "Relancé"
                existing[key]["Date_Relance_Prevue"] = f"Relancé le {today_str}"
                updated += 1
        if updated and self._write_rows(existing):
            logger.info(f"[Suivi Spontanées] {updated} entreprise(s) passée(s) au statut 'Relancé'.")
        return updated
