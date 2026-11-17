"""Orchestrateur de la campagne de candidatures spontanées locales et des relances J+7."""

import argparse
import csv
import logging
import re
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

    companies = (
        [c for c in all_companies if c.department == str(dept_filter)]
        if dept_filter
        else all_companies
    )

    tracker = SpontaneousTracker()
    existing = tracker.load_existing()

    # En mode réel, ne pas renvoyer un premier mail aux entreprises déjà contactées
    if live_send:
        skipped = []
        filtered_companies = []
        for c in companies:
            old_status = (existing.get(c.name.strip().lower(), {}).get("Statut") or "").strip()
            if old_status in tracker.ADVANCED_STATUSES:
                skipped.append(c.name)
            else:
                filtered_companies.append(c)
        if skipped:
            console.print(
                f"[yellow]ℹ {len(skipped)} entreprise(s) ignorée(s) car déjà contactée(s) : {', '.join(skipped)}[/yellow]"
            )
        companies = filtered_companies

    if not companies:
        console.print("[bold yellow]Aucune nouvelle entreprise à contacter sur ce filtre.[/bold yellow]")
        return

    console.print(f"[bold green]✔[/bold green] [cyan]{len(companies)}[/cyan] entreprises cibles sélectionnées.")

    # 1. Génération des messages et lettres PDF
    generator = SpontaneousPitchGenerator()
    applications: List[SpontaneousApplication] = []
    letter_gen = LetterGenerator()
    for c in companies:
        app = generator.generate_application(c)
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
    succeeded_apps: List[SpontaneousApplication] = []
    for app in applications:
        if mailer.send_application(app):
            succeeded_apps.append(app)

    # 6. Mise à jour de la traçabilité (suivi_spontanees.csv) avec J+7
    if live_send:
        if succeeded_apps:
            tracker.record_applications(succeeded_apps, mark_as_sent=True)
    else:
        tracker.record_applications(applications, mark_as_sent=False)

    console.print(
        f"\n[bold green]✔[/bold green] Campagne terminée : [cyan]{len(succeeded_apps)}/{len(applications)}[/cyan] candidatures traitées.\n"
        f"Consultez [bold yellow]suivi_spontanees.csv[/bold yellow] pour suivre les statuts et la date de relance à J+7."
    )


def run_followups(dept_filter: Optional[str] = None, live_send: bool = False):
    """Détecte et envoie les relances J+7 pour les candidatures spontanées au statut 'Envoyé'."""
    console.print(
        Panel(
            "[bold cyan]🔔 RELANCES AUTOMATIQUES À J+7 (CANDIDATURES SPONTANÉES)[/bold cyan]\n"
            f"[white]Candidat :[/white] [bold green]{settings.candidate_name}[/bold green] | "
            f"[white]Mode :[/white] {'[bold red]ENVOI RÉEL (SMTP)[/bold red]' if live_send else '[bold green]SIMULATION (DRY-RUN)[/bold green]'}\n"
            f"[white]Filtre département :[/white] {dept_filter or 'Tous (17, 79, 85, 75)'}",
            border_style="cyan",
        )
    )

    tracker = SpontaneousTracker()
    companies_by_name = {c.name.strip().lower(): c for c in load_target_companies()}
    due_rows = tracker.get_due_followups()

    if dept_filter:
        due_rows = [
            row
            for row in due_rows
            if companies_by_name.get((row.get("Entreprise") or "").strip().lower(), TargetCompany(
                name="", city="", department="", sector="", website="", contact_email=""
            )).department == str(dept_filter)
        ]

    if not due_rows:
        console.print(
            "[bold green]✔[/bold green] Aucune candidature au statut [bold]Envoyé[/bold] n'a encore atteint sa date de relance (J+7)."
        )
        return

    generator = SpontaneousPitchGenerator()
    letter_gen = LetterGenerator()
    followups: List[SpontaneousApplication] = []

    table = Table(title=f"⏰ {len(due_rows)} RELANCE(S) J+7 À EFFECTUER", show_lines=True)
    table.add_column("Entreprise", style="bold white", width=25)
    table.add_column("Ville", style="cyan", width=18)
    table.add_column("Email", style="green", width=28)
    table.add_column("Date Envoi", justify="center", style="yellow", width=12)
    table.add_column("Relance Prévue", justify="center", style="magenta", width=14)

    for row in due_rows:
        company_name = row.get("Entreprise", "").strip()
        city = row.get("Ville", "").strip()
        email = row.get("Email", "").strip()
        sent_date = row.get("Date_Envoi", "").strip()
        due_date = row.get("Date_Relance_Prevue", "").strip()
        notes = row.get("Commentaires", "").strip()
        comp_meta = companies_by_name.get(company_name.lower())
        sector = comp_meta.sector if comp_meta else ""

        app = generator.generate_followup(
            company_name=company_name,
            city=city,
            contact_email=email,
            sent_date=sent_date,
            notes=notes,
        )
        ctx = LetterContext(
            company=re.sub(r"\s*\(.*?\)", "", company_name).strip(),
            address=city,
            sector=sector,
        )
        app.letter_path = str(letter_gen.export_pdf(ctx))
        followups.append(app)
        table.add_row(company_name, city, email, sent_date, due_date)

    console.print(table)

    sample = followups[0]
    console.print(
        Panel(
            f"[bold yellow]Objet :[/bold yellow] {sample.subject}\n"
            f"[bold yellow]Destinataire :[/bold yellow] {sample.company_name} <{sample.contact_email}>\n\n"
            f"{sample.body}",
            title=f"📄 APERÇU RELANCE ({sample.company_name})",
            border_style="yellow",
        )
    )

    if live_send:
        if not settings.smtp.is_configured:
            console.print(
                "[bold red]❌ ERREUR : Identifiants SMTP non configurés dans le fichier .env ![/bold red]\n"
                "Renseigne SMTP_USER et SMTP_PASSWORD pour autoriser l'envoi réel."
            )
            return

        confirm = Confirm.ask(
            f"[bold red]Confirmer l'envoi réel de {len(followups)} mail(s) de relance ?[/bold red]"
        )
        if not confirm:
            console.print("[yellow]Relances annulées par l'utilisateur.[/yellow]")
            return

    mailer = SmtpMailer(dry_run=not live_send)
    succeeded_names: List[str] = []
    for app in followups:
        if mailer.send_application(app):
            succeeded_names.append(app.company_name)

    if live_send and succeeded_names:
        tracker.mark_followed_up(succeeded_names)

    console.print(
        f"\n[bold green]✔[/bold green] Relances terminées : [cyan]{len(succeeded_names)}/{len(followups)}[/cyan] traitée(s)."
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
    parser.add_argument(
        "--relance",
        action="store_true",
        help="Vérifier et envoyer les relances J+7 des candidatures déjà envoyées",
    )

    args = parser.parse_args()
    if args.relance:
        run_followups(dept_filter=args.dept, live_send=args.send)
    else:
        run_campaign(dept_filter=args.dept, live_send=args.send)


if __name__ == "__main__":
    main()
