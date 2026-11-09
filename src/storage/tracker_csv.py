"""Gestionnaire de synchronisation du fichier CSV de suivi des candidatures."""

import csv
import logging
from pathlib import Path
from typing import Dict, List
from config.settings import settings
from src.models import JobOffer

logger = logging.getLogger("stage_agent.storage.csv")


class CsvTracker:
    """Permet de persister et mettre à jour le fichier candidatures.csv de manière incrémentale."""

    FIELDNAMES = [
        "ID",
        "Date",
        "Entreprise",
        "Intitulé",
        "Localisation",
        "Télétravail",
        "Score",
        "Statut",
        "Source",
        "Lien",
        "Compétences",
        "Accroche",
    ]

    def __init__(self, file_path: Path = settings.csv_output_path):
        self.file_path = file_path

    def load_existing(self) -> Dict[str, dict]:
        """Charge les offres existantes depuis le CSV pour préserver les statuts modifiés manuellement."""
        existing: Dict[str, dict] = {}
        if not self.file_path.exists():
            return existing

        try:
            with open(self.file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    offer_id = row.get("ID")
                    if offer_id:
                        existing[offer_id] = row
        except Exception as e:
            logger.warning(f"Impossible de lire l'ancien fichier CSV ({e}). Création d'un nouveau.")

        return existing

    def save_offers(self, offers: List[JobOffer]) -> int:
        """Sauvegarde les offres en fusionnant avec l'existant sans écraser les statuts personnalisés."""
        existing = self.load_existing()
        new_count = 0

        # Mettre à jour la collection
        for offer in offers:
            row = offer.to_csv_dict()
            if offer.id in existing:
                # Préserver le statut manuel défini par l'utilisateur
                old_status = existing[offer.id].get("Statut")
                if old_status and old_status != "À contacter":
                    row["Statut"] = old_status
            else:
                new_count += 1
            existing[offer.id] = row

        # Trier par score décroissant
        sorted_rows = sorted(
            existing.values(),
            key=lambda r: int(r.get("Score", 0)),
            reverse=True,
        )

        try:
            # Encodage utf-8-sig pour compatibilité parfaite Excel sous Windows
            with open(self.file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(sorted_rows)

            logger.info(f"[CSV] {len(sorted_rows)} candidatures enregistrées ({new_count} nouvelles) dans {self.file_path.name}.")
            return new_count
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture du CSV : {e}")
            return 0
