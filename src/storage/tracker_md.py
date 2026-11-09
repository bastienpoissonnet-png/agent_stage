"""Générateur de tableau de bord de suivi au format Markdown (candidatures.md)."""

import csv
from datetime import datetime
import logging
from pathlib import Path
from typing import List
from config.settings import settings
from src.models import JobOffer
from src.storage.tracker_csv import CsvTracker

logger = logging.getLogger("stage_agent.storage.markdown")


class MarkdownTracker:
    """Génère un tableau de bord visuel et interactif en Markdown."""

    def __init__(self, file_path: Path = settings.md_output_path):
        self.file_path = file_path
        self.candidate = settings.profile.get("candidate", {})
        self.search = settings.profile.get("search_criteria", {})

    def generate_dashboard(self, offers: List[JobOffer]) -> None:
        """Génère le fichier candidatures.md incluant les offres et les candidatures spontanées."""
        now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")

        # Fusionner avec les statuts du CSV d'offres
        csv_tracker = CsvTracker()
        existing = csv_tracker.load_existing()

        for o in offers:
            if o.id in existing:
                o.status = existing[o.id].get("Statut", o.status)

        total_offers = len(offers)
        top_offers = [o for o in offers if o.score >= 50]
        status_counts = {}
        for o in offers:
            status_counts[o.status] = status_counts.get(o.status, 0) + 1

        md_content = []
        md_content.append("# 🎯 Suivi des Candidatures de Stage — BUT 3 Data & IA\n")
        md_content.append(
            f"> **Candidat :** {self.candidate.get('name', 'Bastien Poissonnet')}  \n"
            f"> **Période cible :** {self.search.get('internship_period', '22 mars 2027 - fin juin 2027')}  \n"
            f"> **Zones cibles :** La Rochelle (17), Niort (79), La Roche-sur-Yon (85), Paris / IDF (75)  \n"
            f"> **Mode :** Présentiel ou Hybride (Full remote exclu)  \n"
            f"> **Dernière mise à jour :** {now_str}\n"
        )

        md_content.append("## 📊 Tableau de Bord des Offres Détectées (KPIs)\n")
        md_content.append(f"- **Total d'offres qualifiées :** `{total_offers}`")
        md_content.append(f"- **Offres à fort intérêt (Score ≥ 50) :** `{len(top_offers)}`")
        status_line = " | ".join([f"**{st} :** `{nb}`" for st, nb in status_counts.items()])
        md_content.append(f"- **Répartition des statuts :** {status_line}\n")

        # Section 1 : Offres publiées
        if offers:
            md_content.append("## 🚀 Top Offres Publiées (Présentiel & Hybride)\n")
            md_content.append("| Score | Statut | Poste | Entreprise | Lieu | Source | Lien |")
            md_content.append("| :---: | :---: | :--- | :--- | :--- | :---: | :---: |")

            for o in offers[:25]:
                clean_company = o.company[:25]
                clean_title = o.title[:35]
                link_md = f"[Voir l'offre]({o.url})" if o.url.startswith("http") else "—"
                md_content.append(
                    f"| **{o.score}** | `{o.status}` | {clean_title} | {clean_company} | {o.location} | {o.source} | {link_md} |"
                )

            md_content.append("\n---\n")
            md_content.append("## ✉️ Accroches Personnalisées & Fiches Détaillées (Offres publiées)\n")
            md_content.append("*(Clique sur une offre pour déplier le message d'accroche prêt à envoyer)*\n")

            for i, o in enumerate(offers[:15], 1):
                skills_str = ", ".join(o.detected_skills) if o.detected_skills else "Non spécifié"
                reasons_str = "<br>• " + "<br>• ".join(o.match_reasons) if o.match_reasons else "Score standard"

                md_content.append(f"### {i}. [{o.score} pts] {o.title} — {o.company}")
                md_content.append(f"- **Localisation :** {o.location} ({'Hybride' if o.is_remote else 'Présentiel / Sur site'})")
                md_content.append(f"- **Compétences détectées :** `{skills_str}`")
                md_content.append(f"- **Lien direct :** [{o.url}]({o.url})")
                md_content.append(f"- **Détail du scoring :** {reasons_str}")
                md_content.append("")
                md_content.append("<details>")
                md_content.append(f"<summary>👉 <b>Afficher le message d'accroche personnalisé pour {o.company}</b></summary>\n")
                md_content.append("```text")
                md_content.append(o.personalized_pitch)
                md_content.append("```")
                md_content.append("</details>\n")

        # Section 2 : Candidatures Spontanées Locales
        spontaneous_csv = settings.spontaneous_csv_path
        if spontaneous_csv.exists():
            try:
                with open(spontaneous_csv, "r", encoding="utf-8-sig") as f:
                    spont_rows = list(csv.DictReader(f))
                if spont_rows:
                    md_content.append("\n---\n")
                    md_content.append("## 📬 Suivi de la Campagne de Candidatures Spontanées\n")
                    md_content.append("| Entreprise | Ville | Email Contact | Statut | Date Envoi | Relance Prévue (J+7) |")
                    md_content.append("| :--- | :--- | :--- | :---: | :---: | :---: |")
                    for row in spont_rows:
                        md_content.append(
                            f"| **{row.get('Entreprise')}** | {row.get('Ville')} | `{row.get('Email')}` | `{row.get('Statut')}` | {row.get('Date_Envoi')} | **{row.get('Date_Relance_Prevue')}** |"
                        )
                    md_content.append("")
            except Exception as e:
                logger.debug(f"Erreur inclusion suivi spontané : {e}")

        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_content))
            logger.info(f"[Markdown] Dashboard généré dans {self.file_path.name}.")
        except Exception as e:
            logger.error(f"Erreur lors de la génération du Markdown : {e}")
