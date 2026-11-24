"""Génération de lettres de motivation personnalisées à partir du modèle configuré."""

from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import re
from typing import Dict, List, Optional

from config.settings import settings

logger = logging.getLogger("stage_agent.letters")

TEMPLATE_PATH = settings.data_dir / "lettre_type.txt"
EXAMPLE_TEMPLATE_PATH = settings.data_dir / "lettre_type.example.txt"
OUTPUT_DIR = settings.project_root / "letters"

# secteur (mot-clé) -> (accroche, équipe visée, projets visés)
SECTOR_PROFILES = [
    (["assurance", "mutuelle", "banque", "finance"],
     "l'innovation et la valorisation des données au service de ses assurés et de ses métiers",
     "l'équipe Data et IA",
     "l'optimisation des processus métiers, le développement d'outils d'aide à la décision, la mise en place de modèles prédictifs et le déploiement d'outils basés sur l'IA"),
    (["éditeur", "saas", "logiciel", "crm", "erp", "progiciel"],
     "l'innovation et la conception de logiciels de gestion",
     "l'équipe de développement et Data/IA",
     "l'évolution de vos produits logiciels, l'automatisation de traitements de données et l'intégration de fonctionnalités basées sur l'IA"),
    (["conseil", "esn", "services numériques", "ingénierie"],
     "l'innovation et la gestion de projets techniques variés",
     "l'équipe Data et IA",
     "l'optimisation des processus métiers de vos clients, le développement d'outils d'aide à la décision et le déploiement de solutions basées sur l'IA"),
    (["data", "ia", "intelligence artificielle", "science"],
     "l'innovation et le déploiement de solutions Data et IA",
     "l'équipe Data et IA",
     "la mise en place de modèles prédictifs, le traitement avancé des données et le déploiement d'outils basés sur l'IA"),
    (["marketing", "communication", "digital", "agence", "média", "presse"],
     "la créativité et le développement de projets de communication",
     "votre équipe communication et marketing",
     "la création de contenus, le suivi de campagnes et le développement de votre visibilité"),
    (["rh", "ressources humaines", "recrutement"],
     "le développement des talents et l'accompagnement des équipes",
     "votre équipe ressources humaines",
     "la gestion des recrutements, le suivi des collaborateurs et l'amélioration des processus RH"),
    (["commerce", "vente", "retail", "distribution"],
     "le développement commercial et la satisfaction client",
     "votre équipe",
     "le suivi de projets opérationnels, l'analyse de l'activité et l'accompagnement de vos clients"),
    (["industrie", "agro", "iot", "nature", "énergie"],
     "l'innovation et la gestion de projets techniques",
     "votre équipe projets",
     "l'exploitation des données opérationnelles, l'amélioration continue et l'optimisation des processus métiers"),
]
DEFAULT_PROFILE = (
    "l'innovation et la gestion de projets",
    "votre équipe",
    "l'optimisation des processus métiers et la conduite de vos projets actuels",
)


@dataclass
class LetterContext:
    company: str
    address: str = ""
    sector: str = ""
    job_title: str = ""
    offer_skills: Optional[List[str]] = None
    file_stem: str = ""

    @property
    def anonymous(self) -> bool:
        """Entreprise non communiquée dans l'annonce (offres confidentielles)."""
        return self.company.strip().lower().startswith(("confidentiel", "non spécifié", "votre entreprise"))

    @property
    def display_company(self) -> str:
        return "votre entreprise" if self.anonymous else self.company


class LetterGenerator:
    def __init__(self, template_path: Path = TEMPLATE_PATH):
        self.template_path = template_path

    def _read_template(self) -> str:
        if self.template_path.exists():
            return self.template_path.read_text(encoding="utf-8")
        if EXAMPLE_TEMPLATE_PATH.exists():
            return EXAMPLE_TEMPLATE_PATH.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Modèle de lettre introuvable : {self.template_path}")

    @staticmethod
    def _profile_for(sector: str):
        s = sector.lower()
        for keywords, *profile in SECTOR_PROFILES:
            if any(re.search(r"\b" + re.escape(k), s) for k in keywords):
                return tuple(profile)
        return DEFAULT_PROFILE

    @staticmethod
    def _cv_skill_map() -> Dict[str, str]:
        """Construit dynamiquement la table des compétences réelles du candidat."""
        skill_map: Dict[str, str] = {}
        for skill in settings.core_skills + settings.secondary_skills:
            clean = skill.strip()
            if not clean:
                continue
            for token in re.split(r"[/,]", clean):
                t = token.strip()
                if t:
                    skill_map.setdefault(t.lower(), t)
            if clean.lower() == "powerbi":
                skill_map["power bi"] = "PowerBI"
        return skill_map

    def _common_skills(self, offer_skills: Optional[List[str]]) -> List[str]:
        skill_map = self._cv_skill_map()
        found: List[str] = []
        for raw in offer_skills or []:
            for token in re.split(r"[/,]", raw):
                label = skill_map.get(token.strip().lower())
                if label and label not in found:
                    found.append(label)
        return found

    def _offer_sentence(self, ctx: LetterContext) -> str:
        if not ctx.job_title:
            return ""
        skills = self._common_skills(ctx.offer_skills)
        sentence = f"Votre offre « {ctx.job_title.strip()} » a particulièrement retenu mon attention"
        if skills:
            sentence += f", notamment par les compétences que je pratique déjà ({', '.join(skills)})"
        return sentence + ". "

    def render(self, ctx: LetterContext) -> str:
        candidate = settings.profile.get("candidate", {})
        search = settings.profile.get("search_criteria", {})
        accroche, equipe, projets = self._profile_for(ctx.sector)

        project_highlight = (candidate.get("project_highlight") or "").strip()
        phrase_projet = f" {project_highlight}" if project_highlight else ""
        exp_summary = (candidate.get("experience_summary") or "").strip()
        if not exp_summary:
            exps = settings.profile.get("experiences", [])
            if exps:
                exp_summary = exps[0].get("summary", "")

        competences = ", ".join((settings.core_skills + settings.secondary_skills)[:6])

        text = self._read_template()
        values = {
            "{nom_entreprise}": ctx.display_company,
            "{adresse_entreprise}": ctx.address,
            "{accroche_entreprise}": accroche,
            "{equipe_cible}": equipe,
            "{projets_vises}": projets,
            "{phrase_offre}": self._offer_sentence(ctx),
            "{phrase_projet}": phrase_projet,
            "{nom_candidat}": candidate.get("name", ""),
            "{formation}": candidate.get("degree", ""),
            "{specialite}": candidate.get("specialty", ""),
            "{ecole}": candidate.get("school", ""),
            "{periode_stage}": search.get("internship_period", ""),
            "{duree_semaines}": str(search.get("duration_weeks", "")),
            "{competences_cles}": competences,
            "{experience_resume}": exp_summary,
        }
        for token, value in values.items():
            text = text.replace(token, value)
        return text

    def header_lines(self, ctx: LetterContext) -> List[str]:
        c = settings.profile.get("candidate", {})
        return [
            c.get("name", ""),
            c.get("location", ""),
            c.get("phone", ""),
            c.get("email", ""),
            "",
            *([] if ctx.anonymous else [ctx.company]),
            *([ctx.address] if ctx.address and not ctx.anonymous else []),
        ]

    def export_pdf(self, ctx: LetterContext, output_dir: Path = OUTPUT_DIR) -> Path:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from xml.sax.saxutils import escape

        output_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9]+", "_", ctx.file_stem or ctx.company).strip("_") or "entreprise"
        path = output_dir / f"{datetime.now():%Y%m%d}_Lettre_{safe}.pdf"
        author = settings.candidate_name or "Candidat"

        body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=14.5, spaceAfter=8)
        head = ParagraphStyle("head", parent=body, spaceAfter=0, leading=13)
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=2.2 * cm,
            rightMargin=2.2 * cm,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
            title=f"Lettre de motivation - {ctx.company}",
            author=author,
        )
        story = [Paragraph(escape(line) or "&nbsp;", head) for line in self.header_lines(ctx)]
        story.append(Spacer(1, 0.6 * cm))
        for block in self.render(ctx).split("\n\n"):
            story.append(Paragraph(escape(block).replace("\n", "<br/>"), body))
        doc.build(story)
        logger.info(f"Lettre générée : {path}")
        return path
