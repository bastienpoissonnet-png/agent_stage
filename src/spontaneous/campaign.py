"""Orchestrateur de la campagne de candidatures spontanées locales."""

import argparse
import csv
import re
import logging
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from config.settings import settings
from src.letters import LetterContext, LetterGenerator
from src.spontaneous.mailer import SmtpMailer
from src.spontaneous.models import SpontaneousApplication, TargetCompany
from src.spontaneous.pitch_generator import SpontaneousPitchGenerator
from src.spontaneous.tracker import SpontaneousTracker

logger = logging.getLogger("stage_agent.spontaneous.campaign")
console = Console()


def load_target_companies(file_path: Path = settings.target_companies_path) -> List[TargetCompany]:
    """Charge la liste des entreprises cibles depuis target_companies.csv."""
    if not file_path.exists():
        logger.error(f"Fichier de ciblage introuvable : {file_path}")
        return []

    companies = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Nom"):
                continue
            companies.append(
                TargetCompany(
                    name=row.get("Nom", "").strip(),
                    city=row.get("Ville", "").strip(),
                    department=row.get("Departement", "").strip(),
                    sector=row.get("Secteur", "").strip(),
                    website=row.get("Site_Web", "").strip(),
                    contact_email=row.get("Email_Contact", "").strip(),
                    context_note=row.get("Note_Contexte", "").strip(),
                )
            )
    return companies


def run_campaign(
    dept_filter: Optional[str] = None,
    live_send: bool = False,
    preview_limit: int = 2,
):
    """Exécute la campagne de candidatures spontanées."""
    console.print(
        Panel(
            "[bold cyan]📬 CAMPAGNE DE CANDIDATURES SPONTANÉES LOCALES[/bold cyan]\n"
            f"[white]Candidat :[/white] [bold green]{settings.candidate_name}[/bold green] | "
            f"[white]Mode :[/white] {'[bold red]ENVOI RÉEL (SMTP)[/bold red]' if live_send else '[bold green]SIMULATION (DRY-RUN)[/bold green]'}\n"
            f"[white]Filtre département :[/white] {dept_filter or 'Tous (17, 79, 85, 75)'}",
            border_style="cyan",
        )
    )

    all_companies = load_target_companies()
    if not all_companies:
        console.print("[bold red]Aucune entreprise trouvée dans data/target_companies.csv ![/bold red]")
        return

    # Filtrage par département
    if dept_filter:
        companies = [c for c in all_companies if c.department == str(dept_filter)]
    else:
        companies = all_companies

    console.print(f"[bold green]✔[/bold green] [cyan]{len(companies)}[/cyan] entreprises cibles sélectionnées.")

    # 1. Génération des messages d'accroche
    generator = SpontaneousPitchGenerator()
    applications: List[SpontaneousApplication] = []
    letter_gen = LetterGenerator()
    for c in companies:
        app = generator.generate_application(c)
        # Lettre de motivation personnalisée (PDF) générée à partir du modèle type
        ctx = LetterContext(company=re.sub(r"\s*\(.*?\)", "", c.name).strip(), address=c.city, sector=c.sector)
        app.letter_path = str(letter_gen.export_pdf(ctx))
        applications.append(app)

    # 2. Affichage récapitulatif
    table = Table(title="🏢 ENTREPRISES CIBLES SÉLECTIONNÉES", show_lines=True)
    table.add_column("Entreprise", style="bold white", width=25)
    table.add_column("Ville", style="cyan", width=18)
    table.add_column("Dép.", justify="center", style="yellow", width=6)
    table.add_column("Secteur d'activité", style="magenta", width=28)
    table.add_column("Email Recrutement", style="green", width=28)

    for c in companies:
        table.add_row(c.name, c.city, c.department, c.sector[:26], c.contact_email)

    console.print(table)

    # 3. Prévisualisation d'un email généré
    if applications:
        sample_app = applications[0]
        preview_panel = Panel(
            f"[bold yellow]Objet :[/bold yellow] {sample_app.subject}\n"
            f"[bold yellow]Destinataire :[/bold yellow] {sample_app.company_name} <{sample_app.contact_email}>\n\n"
            f"{sample_app.body}",
            title=f"📄 EXEMPLE DE MAIL GÉNÉRÉ ({sample_app.company_name})",
            border_style="yellow",
        )
        console.print(preview_panel)

    # 4. Confirmation avant envoi réel
    if live_send:
        if not settings.smtp.is_configured:
            console.print(
                "[bold red]❌ ERREUR : Identifiants SMTP non configurés dans le fichier .env ![/bold red]\n"
                "Renseigne SMTP_USER et SMTP_PASSWORD pour autoriser l'envoi réel."
            )
            return

        confirm = Confirm.ask(
            f"[bold red]Êtes-vous sûr de vouloir envoyer {len(applications)} emails réels maintenant ?[/bold red]"
        )
        if not confirm:
            console.print("[yellow]Opération annulée par l'utilisateur.[/yellow]")
            return

    # 5. Envoi ou simulation
    mailer = SmtpMailer(dry_run=not live_send)
    sent_count = 0
    for app in applications:
        success = mailer.send_application(app)
        if success:
            sent_count += 1

    # 6. Mise à jour de la traçabilité (suivi_spontanees.csv) avec J+7
    tracker = SpontaneousTracker()
    tracker.record_applications(applications, mark_as_sent=live_send)

    console.print(
        f"\n[bold green]✔[/bold green] Campagne terminée : [cyan]{sent_count}/{len(applications)}[/cyan] candidatures traitées.\n"
        f"Consultez [bold yellow]suivi_spontanees.csv[/bold yellow] pour suivre les statuts et la date de relance à J+7."
    )


def main():
    parser = argparse.ArgumentParser(description="Campagne de candidatures spontanées locales")
    parser.add_argument(
        "--dept",
        choices=["17", "79", "85", "75"],
        help="Filtrer par département cible (17: La Rochelle, 79: Niort, 85: La Roche-sur-Yon, 75: Paris)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Déclencher l'envoi réel via SMTP (par défaut: simulation Dry-Run sans envoi)",
    )

    args = parser.parse_args()
    run_campaign(dept_filter=args.dept, live_send=args.send)


if __name__ == "__main__":
    main()

