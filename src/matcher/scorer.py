"""Moteur de scoring pondéré favorisant le présentiel local et les compétences Data/IA."""

import logging
import re
from typing import List, Set
from config.settings import settings
from src.models import JobOffer

logger = logging.getLogger("stage_agent.matcher.scorer")


class JobScorer:
    """Calcule un score d'adéquation sur 100 favorisant le présentiel local et la stack de Bastien."""

    def __init__(self):
        self.core_skills = settings.core_skills
        self.secondary_skills = settings.secondary_skills

    def _extract_skills(self, text: str) -> List[str]:
        """Extrait les technologies mentionnées dans le titre et la description."""
        found: Set[str] = set()
        text_lower = f" {text.lower()} "

        skills_to_check = {
            "Python": [r"\bpython\b", r"\bpy\b"],
            "SQL": [r"\bsql\b", r"\bpostgres\b", r"\bmysql\b"],
            "Elasticsearch": [r"\belasticsearch\b", r"\belastic\b", r"\belk\b"],
            "Data / IA": [
                r"\bdata\b",
                r"\bia\b",
                r"\bartificial intelligence\b",
                r"\bintelligence artificielle\b",
                r"\bmachine learning\b",
                r"\bdeep learning\b",
                r"\bdata engineer\b",
                r"\bdata science\b",
            ],
            "Rust": [r"\brust\b"],
            "C++ / C": [r"\bc\+\+\b", r"\bc\b(?!\w)"],
            "React / JS": [r"\breact\b", r"\bjavascript\b", r"\btypescript\b"],
            "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
            "Bash / Linux": [r"\bbash\b", r"\blinux\b", r"\bshell\b"],
            "Docker": [r"\bdocker\b", r"\bconteneur\b"],
            "Agile / Scrum": [r"\bagile\b", r"\bscrum\b"],
        }

        for skill_name, patterns in skills_to_check.items():
            for p in patterns:
                if re.search(p, text_lower):
                    found.add(skill_name)
                    break

        return sorted(list(found))

    def score_offer(self, offer: JobOffer) -> JobOffer:
        """Calcule le score de pertinence et enrichit l'objet JobOffer."""
        full_text = f"{offer.title} {offer.description}".lower()
        title_lower = offer.title.lower()
        score = 0
        reasons = []

        # 1. Correspondance type de contrat : Stage de fin d'études / BUT3
        stage_kws = ["stage", "stagiaire", "internship", "intern", "fin d'études", "pfe", "but 3", "bac+3"]
        if any(kw in title_lower for kw in stage_kws):
            score += 35
            reasons.append("+35: Intitulé de stage explicite")
        elif any(kw in full_text for kw in stage_kws) or offer.contract_type == "Stage":
            score += 25
            reasons.append("+25: Stage conventionné")
        elif any(kw in title_lower for kw in ["junior", "débutant", "entry level"]):
            score += 15
            reasons.append("+15: Poste junior accessible")

        # 2. Compétences détectées (+10 pts cœur, +5 pts secondaires)
        detected = self._extract_skills(full_text)
        offer.detected_skills = detected

        for skill in detected:
            if skill in ["Python", "SQL", "Elasticsearch", "Data / IA"]:
                score += 10
                reasons.append(f"+10: Compétence cœur ({skill})")
            else:
                score += 5
                reasons.append(f"+5: Compétence complémentaire ({skill})")

        # 3. Adéquation géographique stricte (Présentiel / Hybride prioritaire)
        loc_lower = f"{offer.location} {full_text}".lower()

        if "la rochelle" in loc_lower or (offer.department == "17"):
            score += 30
            reasons.append("+30: Priorité absolue La Rochelle (IUT)")
        elif "niort" in loc_lower or (offer.department == "79"):
            score += 25
            reasons.append("+25: Pôle Niort (Mutuelles / Assurance Tech)")
        elif "la roche-sur-yon" in loc_lower or (offer.department == "85"):
            score += 25
            reasons.append("+25: Pôle La Roche-sur-Yon / Vendée (Domicile)")
        elif any(idf in loc_lower for idf in ["paris", "île-de-france", "ile-de-france"]) or (
            offer.department in ["75", "92", "93", "94"]
        ):
            score += 20
            reasons.append("+20: Pôle Paris / Île-de-France")

        # 4. Mode de travail : valorisation du présentiel ou hybride local
        if any(h in full_text for h in ["hybride", "présentiel", "sur site"]):
            score += 10
            reasons.append("+10: Mode de travail hybride ou sur site confirmé")

        # Pénalité sévère si full remote
        if offer.is_remote or "full remote" in full_text or "100% remote" in full_text:
            score -= 30
            reasons.append("-30: Offre full-remote (critère de recherche défavorable)")

        # 5. Bonus contexte éditeur de logiciel / SaaS (expérience Orisha)
        if any(kw in full_text for kw in ["saas", "erp", "logiciel de gestion", "éditeur", "orisha"]):
            score += 10
            reasons.append("+10: Secteur éditeur de logiciels / SaaS (expérience Orisha)")

        # Bornage 0 - 100
        final_score = max(0, min(100, score))
        offer.score = final_score
        offer.match_reasons = reasons

        return offer

    def score_all(self, offers: List[JobOffer]) -> List[JobOffer]:
        """Scoring et tri par pertinence décroissante."""
        scored = [self.score_offer(o) for o in offers]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored
