"""Moteur de scoring pondéré dynamique basé sur le profil utilisateur."""

import logging
import re
from typing import Dict, List, Set, Tuple
from config.settings import settings
from src.models import JobOffer

logger = logging.getLogger("stage_agent.matcher.scorer")

# Alias de recherche enrichis pour les compétences techniques courantes
KNOWN_SKILL_ALIASES: Dict[str, List[str]] = {
    "python": [r"\bpython\b", r"\bpy\b"],
    "sql": [r"\bsql\b", r"\bpostgres\b", r"\bmysql\b"],
    "elasticsearch": [r"\belasticsearch\b", r"\belastic\b", r"\belk\b"],
    "data": [r"\bdata\b", r"\bdata engineer\b", r"\bdata science\b", r"\bdata analyst\b"],
    "intelligence artificielle": [r"\bia\b", r"\bartificial intelligence\b", r"\bintelligence artificielle\b"],
    "machine learning": [r"\bmachine learning\b", r"\bdeep learning\b"],
    "deep learning": [r"\bdeep learning\b"],
    "rust": [r"\brust\b"],
    "c++": [r"\bc\+\+\b"],
    "c": [r"\bc\b(?!\w|\+|#)"],
    "c#": [r"\bc#\b", r"\bcsharp\b"],
    "react": [r"\breact\b"],
    "javascript": [r"\bjavascript\b", r"\btypescript\b", r"\bjs\b"],
    "html/css": [r"\bhtml\b", r"\bcss\b"],
    "git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    "bash": [r"\bbash\b", r"\bshell\b"],
    "linux": [r"\blinux\b"],
    "docker": [r"\bdocker\b", r"\bconteneur\b"],
    "powerbi": [r"\bpower\s*bi\b", r"\bpowerbi\b"],
    "agile": [r"\bagile\b", r"\bscrum\b"],
}


class JobScorer:
    """Calcule un score d'adéquation sur 100 à partir des compétences et zones du profil."""

    def __init__(self):
        self.core_skills = [s.strip() for s in settings.core_skills if s.strip()]
        self.secondary_skills = [s.strip() for s in settings.secondary_skills if s.strip()]
        self.target_locations = [l.strip() for l in settings.target_locations if l.strip()]
        self.target_depts = set(settings.target_departments)

    def _build_skill_patterns(self, skill: str) -> List[str]:
        key = skill.lower()
        if key in KNOWN_SKILL_ALIASES:
            return KNOWN_SKILL_ALIASES[key]
        # Générer une regex sûre pour toute compétence libre (Excel, SEO, Canva, RH, etc.)
        tokens = [t.strip() for t in re.split(r"[/,]", skill) if t.strip()]
        return [r"\b" + re.escape(t.lower()) + r"\b" for t in tokens]

    def _extract_skills(self, text: str) -> Tuple[List[str], List[str]]:
        """Retourne (compétences_cœur_détectées, compétences_secondaires_détectées)."""
        text_lower = f" {text.lower()} "
        core_found: List[str] = []
        sec_found: List[str] = []
        seen: Set[str] = set()

        for skill in self.core_skills:
            if any(re.search(p, text_lower) for p in self._build_skill_patterns(skill)):
                if skill.lower() not in seen:
                    core_found.append(skill)
                    seen.add(skill.lower())

        for skill in self.secondary_skills:
            if skill.lower() in seen:
                continue
            if any(re.search(p, text_lower) for p in self._build_skill_patterns(skill)):
                sec_found.append(skill)
                seen.add(skill.lower())

        return core_found, sec_found

    def score_offer(self, offer: JobOffer) -> JobOffer:
        """Calcule le score de pertinence et enrichit l'objet JobOffer."""
        full_text = f"{offer.title} {offer.description}".lower()
        title_lower = offer.title.lower()
        score = 0
        reasons: List[str] = []

        # 1. Correspondance stage
        stage_kws = ["stage", "stagiaire", "internship", "intern", "fin d'études", "pfe", "but", "bac+"]
        if any(kw in title_lower for kw in stage_kws):
            score += 35
            reasons.append("+35: Intitulé de stage explicite")
        elif any(kw in full_text for kw in stage_kws) or offer.contract_type == "Stage":
            score += 25
            reasons.append("+25: Stage conventionné")
        elif any(kw in title_lower for kw in ["junior", "débutant", "entry level"]):
            score += 15
            reasons.append("+15: Poste junior accessible")

        # 2. Compétences détectées depuis profile.json
        core_found, sec_found = self._extract_skills(full_text)
        offer.detected_skills = core_found + sec_found

        for skill in core_found:
            score += 10
            reasons.append(f"+10: Compétence cœur ({skill})")
        for skill in sec_found:
            score += 5
            reasons.append(f"+5: Compétence complémentaire ({skill})")

        # 3. Adéquation géographique dynamique
        loc_lower = f"{offer.location} {full_text}".lower()
        matched_loc = next((loc for loc in self.target_locations if loc.lower() in loc_lower), None)
        if matched_loc:
            bonus = 30 if matched_loc == self.target_locations[0] else 25
            score += bonus
            reasons.append(f"+{bonus}: Zone cible ({matched_loc})")
        elif offer.department and offer.department in self.target_depts:
            score += 25
            reasons.append(f"+25: Département cible ({offer.department})")

        # 4. Mode de travail
        if any(h in full_text for h in ["hybride", "présentiel", "sur site"]):
            score += 10
            reasons.append("+10: Mode hybride ou présentiel confirmé")
        elif settings.allow_remote and (offer.is_remote or "télétravail" in full_text or "remote" in full_text):
            score += 10
            reasons.append("+10: Télétravail accepté")

        if settings.disallow_full_remote and (
            offer.is_remote or "full remote" in full_text or "100% remote" in full_text
        ):
            score -= 30
            reasons.append("-30: Offre full-remote (non souhaité)")

        # 5. Bonus mots-clés secteur configurés
        bonus_kws = settings.bonus_sector_keywords
        if bonus_kws and any(kw in full_text for kw in bonus_kws):
            score += 10
            reasons.append("+10: Secteur / mot-clé prioritaire du profil")

        # 6. Pénalité alternance si recherche stricte de stage
        if settings.exclude_alternance and any(
            re.search(r"\b" + kw + r"\b", full_text)
            for kw in ["alternance", "alternant", "alternante", "apprentissage", "apprenti", "contrat pro"]
        ):
            score -= 45
            reasons.append("-45: Mention d'alternance/apprentissage")

        offer.score = max(0, min(100, score))
        offer.match_reasons = reasons
        return offer

    def score_all(self, offers: List[JobOffer]) -> List[JobOffer]:
        """Scoring et tri par pertinence décroissante."""
        scored = [self.score_offer(o) for o in offers]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored
