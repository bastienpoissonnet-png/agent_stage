"""Point d'entrée principal (CLI) du Stage Agent.

Orchestre la recherche de stage ciblée (France Travail / French Tech)
ET la campagne de candidatures spontanées locales (La Rochelle, Niort, Vendée, Paris).
"""

import argparse
import logging
import re
import sys
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from config.settings import settings
from src.collectors import (
    FranceTravailCollector,
    FrenchTechCollector,
    WelcomeToTheJungleCollector,
)
from src.letters import LetterContext, LetterGenerator
from src.matcher import JobFilter, JobScorer
from src.models import JobOffer
from src.spontaneous.campaign import run_campaign
from src.storage import CsvTracker, MarkdownTracker

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("stage_agent")
console = Console()


def display_banner():
    """Affiche la bannière d'accueil du profil."""
    candidate = settings.profile.get("candidate", {})
    search = settings.profile.get("search_criteria", {})
    banner_text = (
        f"[bold cyan]🎯 STAGE AGENT — RECHERCHE & CANDIDATURES BUT 3 DATA / IA[/bold cyan]\n"
        f"[white]Candidat :[/white] [bold green]{candidate.get('name')}[/bold green] | "
        f"[white]Formation :[/white] [bold yellow]{candidate.get('degree')}[/bold yellow] ({candidate.get('specialty')})\n"
        f"[white]Période :[/white] {search.get('internship_period')} | "
        f"[white]Mode :[/white] [bold]Présentiel & Hybride (17, 79, 85, 75)[/bold]"
    )
    console.print(Panel(banner_text, border_style="cyan"))


def run_job_search(source_filter: str = "all", min_score: int = 40, limit: int = 30):
    """Exécute le pipeline de veille sur les offres françaises publiées."""
    display_banner()

    collectors = []
    if source_filter in ("all", "ft", "france_travail"):
        collectors.append(FranceTravailCollector())
    if source_filter in ("all", "wttj", "welcome_to_the_jungle"):
        collectors.append(WelcomeToTheJungleCollector())
    if source_filter in ("all", "french_tech"):
        collectors.append(FrenchTechCollector())

    all_raw_offers: List[JobOffer] = []

    # 1. Collecte
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        for collector in collectors:
            task = progress.add_task(f"Interrogation de {collector.name}...", total=None)
            try:
                offers = collector.fetch_offers(limit=limit)
                all_raw_offers.extend(offers)
            except Exception as e:
                logger.error(f"Erreur sur {collector.name}: {e}")
            progress.remove_task(task)

    console.print(f"[bold green]✔[/bold green] Collecte terminée : [cyan]{len(all_raw_offers)}[/cyan] offres collectées.")

    # 2. Filtrage strict (anti-senior, anti-commercial, anti-full-remote, géo-centré)
    job_filter = JobFilter()
    eligible_offers = job_filter.filter_offers(all_raw_offers)

    # 3. Scoring favorisant présentiel local et compétences clés
    scorer = JobScorer()
    scored_offers = scorer.score_all(eligible_offers)

    qualified_offers = [o for o in scored_offers if o.score >= min_score]
    console.print(
        f"[bold green]✔[/bold green] [cyan]{len(qualified_offers)}[/cyan] offres qualifiées retenues (Score ≥ {min_score}/100, Présentiel/Hybride)."
    )

    # 4. Lettres de motivation personnalisées (uniquement pour les nouvelles offres)
    new_offers: List[JobOffer] = []
    if qualified_offers:
        csv_tracker = CsvTracker()
        known = csv_tracker.load_existing()
        new_offers = [o for o in qualified_offers if o.id not in known]

        letter_gen = LetterGenerator()
        for o in qualified_offers:
            ctx = LetterContext(
                company=o.company,
                address=re.sub(r"^\d{2,3}\s*-\s*", "", o.location or ""),
                job_title=re.sub(r"\s*\((H/F|F/H)\)\s*", " ", o.title).strip(),
                offer_skills=o.detected_skills,
                file_stem=f"{o.company}_{o.id[:6]}",
            )
            o.personalized_pitch = letter_gen.render(ctx)
            if o in new_offers or not known.get(o.id, {}).get("Lettre"):
                try:
                    o.letter_path = str(letter_gen.export_pdf(ctx))
                except Exception as e:
                    logger.error(f"Lettre non générée pour {o.title}: {e}")

        # 5. Sauvegarde locale
        new_count = csv_tracker.save_offers(qualified_offers)

        md_tracker = MarkdownTracker()
        md_tracker.generate_dashboard(qualified_offers)

        console.print(
            f"[bold green]✔[/bold green] Synchronisation : [cyan]{new_count}[/cyan] nouvelles offres ajoutées dans [bold]candidatures.csv[/bold] et [bold]candidatures.md[/bold] "
            f"([cyan]{len(new_offers)}[/cyan] lettres PDF générées dans [bold]letters/[/bold]).\n"
        )
        display_summary_table(qualified_offers[:10])
    else:
        # Régénérer le markdown pour mettre à jour la date et garder la section spontanée
        MarkdownTracker().generate_dashboard([])
        console.print(
            "[bold yellow]ℹ Aucune offre ne correspond aux critères stricts pour le moment.\n"
            "Conseil : Renseigne tes clés France Travail dans .env pour interroger le vivier officiel, "
            "ou lance une campagne de candidatures spontanées locales avec :[/bold yellow] [bold green]python main.py --spontaneous[/bold green]"
        )

    return new_offers


def display_summary_table(offers: List[JobOffer]):
    """Affiche un tableau clair des meilleures opportunités."""
    table = Table(title="🏆 TOP DES OFFRES SÉLECTIONNÉES (PRÉSENTIEL / HYBRIDE)", show_lines=True)
    table.add_column("Score", justify="center", style="bold green", width=7)
    table.add_column("Poste", style="cyan", width=30)
    table.add_column("Entreprise", style="white", width=22)
    table.add_column("Lieu", style="yellow", width=20)
    table.add_column("Stack détectée", style="magenta", width=22)
    table.add_column("Source", style="blue", width=16)

    for o in offers:
        skills = ", ".join(o.detected_skills) if o.detected_skills else "Data / Tech"
        table.add_row(
            str(o.score),
            o.title[:29],
            o.company[:21],
            o.location[:19],
            skills[:21],
            o.source[:15],
        )

    console.print(table)
    console.print("\n[bold cyan]👉 Prochaines étapes :[/bold cyan]")
    console.print("1. Ouvre [bold yellow]candidatures.md[/bold yellow] pour lire les fiches et copier les messages d'accroche.")
    console.print("2. Ouvre [bold yellow]candidatures.csv[/bold yellow] pour suivre l'avancement.")


def main():
    parser = argparse.ArgumentParser(description="Stage Agent — Veille de stages et candidatures spontanées")

    # Lettre de motivation ponctuelle
    parser.add_argument("--letter", metavar="ENTREPRISE", help="Générer une lettre de motivation PDF pour cette entreprise")
    parser.add_argument("--address", default="", help="Adresse de l'entreprise (optionnel, avec --letter)")
    parser.add_argument("--sector", default="", help="Secteur de l'entreprise : assurance, éditeur, ESN, data... (avec --letter)")
    parser.add_argument("--job-title", default="", help="Intitulé de l'offre visée (avec --letter)")

    # Mode Spontané
    parser.add_argument(
        "--spontaneous",
        action="store_true",
        help="Lancer la campagne de candidatures spontanées locales (sourcing + emails)",
    )
    parser.add_argument(
        "--dept",
        choices=["17", "79", "85", "75"],
        help="Filtrer les entreprises spontanées par département (17: La Rochelle, 79: Niort, 85: La Roche, 75: Paris)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Déclencher l'envoi réel des emails via SMTP (par défaut: simulation Dry-Run sans envoi)",
    )

    # Mode Veille / Offres
    parser.add_argument(
        "--source",
        choices=["all", "france_travail", "ft", "wttj", "french_tech"],
        default="all",
        help="Source d'offres à interroger (défaut: all)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=settings.min_score_threshold,
        help="Score minimal pour retenir une offre (défaut: 40)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=settings.max_offers_per_source,
        help="Nombre maximal d'offres par source (défaut: 30)",
    )

    args = parser.parse_args()

    if args.letter:
        from src.letters import LetterContext, LetterGenerator

        ctx = LetterContext(
            company=args.letter,
            address=args.address,
            sector=args.sector,
            job_title=args.job_title,
        )
        gen = LetterGenerator()
        path = gen.export_pdf(ctx)
        console.print(Panel(gen.render(ctx), title="Aperçu de la lettre", border_style="green"))
        console.print(f"[bold green]✔[/bold green] Lettre PDF générée : [bold]{path}[/bold]")
    elif args.spontaneous:
        run_campaign(dept_filter=args.dept, live_send=args.send)
    else:
        run_job_search(source_filter=args.source, min_score=args.min_score, limit=args.limit)


if __name__ == "__main__":
    main()
