"""Filtre d'exclusion configurable pour écarter les offres non pertinentes selon le profil."""

import logging
import re
from typing import List
from config.settings import settings
from src.models import JobOffer

logger = logging.getLogger("stage_agent.matcher.filter")


class JobFilter:
    """Filtre les offres non éligibles selon les critères du profil configuré."""

    def __init__(self):
        self.target_locations = [loc.lower() for loc in settings.target_locations if loc.strip()]
        self.target_depts = set(settings.target_departments)
        self.disallow_full_remote = settings.disallow_full_remote
        self.allow_remote = settings.allow_remote
        self.exclude_alternance = settings.exclude_alternance
        self.exclude_non_tech = settings.exclude_non_tech
        self.custom_excluded_titles = settings.excluded_title_keywords

        # Toujours exclus (stages collège / observation)
        self.always_excluded_keywords = [
            "stage 3eme",
            "stage 3e",
            "stage de 3ème",
            "stage découverte",
            "stage d'observation",
        ]

        # Intitulés non-tech / commerciaux (appliqués uniquement si exclude_non_tech=True)
        self.non_tech_job_keywords = [
            "sales",
            "commercial",
            "account manager",
            "business dev",
            "business developer",
            "business developper",
            "bizdev",
            "growth",
            "marketing",
            "rh",
            "ressources humaines",
            "recrutement",
            "recruteur",
            "communication",
            "community manager",
            "service management",
            "copywriter",
            "support client",
            "service client",
            "comptable",
            "comptabilité",
            "juriste",
            "avocat",
            "assistant administratif",
            "trader",
            "finance",
            "chef d'équipe",
            "vendeur",
            "vendeuse",
            "employé commercial",
            "conducteur",
            "ingénieur d'affaires",
            "ingenieur d'affaires",
            "relation client",
        ]

        # Postes à responsabilité / seniors
        self.senior_keywords = [
            "senior",
            "sr.",
            "lead",
            "architect",
            "architecte",
            "staff",
            "head of",
            "director",
            "directeur",
            "vp of",
            "principal",
        ]

        # Signaux de full remote strict
        self.full_remote_keywords = [
            "full remote",
            "full-remote",
            "100% remote",
            "100% télétravail",
            "télétravail total",
            "remote only",
            "anywhere",
            "work from anywhere",
        ]

        # Signaux d'alternance et apprentissage
        self.alternance_patterns = [
            r"\balternan[ct]e?s?\b",
            r"\balternace\b",
            r"\bapprenti[es]?\b",
            r"\bapprentissage\b",
            r"\bcontrat\s+pro\b",
            r"\bcontrat\s+de\s+pro\b",
            r"\bcontrat\s+de\s+professionnalisation\b",
            r"\bcontrat\s+d['’]apprentissage\b",
            r"\bformation\s+en\s+alternance\b",
            r"\brythme\s+d['’]alternance\b",
            r"\bcalendrier\s+d['’]alternance\b",
        ]

        # Mots-clés rédhibitoires dans la description
        self.strict_exclusion_keywords = [
            "5 ans d'expérience minimum",
        ]
        if self.exclude_alternance:
            self.strict_exclusion_keywords.extend([
                "uniquement en alternance",
                "contrat d'apprentissage uniquement",
                "contrat pro uniquement",
                "pas de stage",
            ])

    def is_eligible(self, offer: JobOffer) -> bool:
        """Vérifie si l'offre respecte les critères configurés dans profile.json."""
        title_lower = f" {offer.title.lower()} "
        text_lower = f"{offer.title} {offer.description}".lower()

        # 1. Exclusions systématiques (stage 3ème / observation) et exclusions personnalisées
        for bad in self.always_excluded_keywords + self.custom_excluded_titles:
            if bad and re.search(r"\b" + re.escape(bad) + r"\b", title_lower):
                logger.debug(f"Offre écartée ({bad}): {offer.title}")
                return False

        # 1b. Exclusion des métiers non-tech si activée dans le profil
        if self.exclude_non_tech:
            for non_tech in self.non_tech_job_keywords:
                if re.search(r"\b" + re.escape(non_tech) + r"\b", title_lower):
                    logger.debug(f"Offre non-tech écartée ({non_tech}): {offer.title}")
                    return False

        # 2. Exclusion des intitulés seniors / architectes sauf si explicité comme stage
        is_explicit_stage = any(
            k in title_lower for k in ["stage", "stagiaire", "intern", "internship", "trainee", "etudiant"]
        )
        if not is_explicit_stage:
            for senior_term in self.senior_keywords:
                if re.search(r"\b" + re.escape(senior_term) + r"\b", title_lower):
                    logger.debug(f"Offre senior écartée ({senior_term}): {offer.title}")
                    return False

        # 3. Exclusion du Full Remote (si disallow_full_remote=True)
        if self.disallow_full_remote:
            for fr_kw in self.full_remote_keywords:
                if fr_kw in text_lower or fr_kw in offer.location.lower():
                    logger.debug(f"Offre écartée car full remote strict : {offer.title}")
                    return False
            if offer.location.strip().lower() in ("remote", "anywhere", "remote / à préciser") and not any(
                loc in text_lower for loc in self.target_locations
            ):
                logger.debug(f"Offre full remote écartée (pas de ville cible) : {offer.title}")
                return False

        # 4. Exclusion des alternances et contrats d'apprentissage (si exclude_alternance=True)
        if self.exclude_alternance:
            has_alternance_signal = any(re.search(pat, text_lower) for pat in self.alternance_patterns)
            if has_alternance_signal:
                has_stage_in_title = any(
                    re.search(r"\b" + kw + r"\b", title_lower)
                    for kw in ["stage", "stagiaire", "intern", "internship", "pfe"]
                )
                has_alternance_in_title = any(re.search(pat, title_lower) for pat in self.alternance_patterns)

                if has_alternance_in_title and not has_stage_in_title:
                    logger.debug(f"Offre d'alternance pure écartée (titre) : {offer.title}")
                    return False

                stage_open_patterns = [
                    r"\bstage\s+(ou|/|\&|et)\s+alternan",
                    r"\balternan[ct]e?\s+(ou|/|\&|et)\s+stage",
                    r"\bouvert\s+au[x]?\s+stage",
                    r"\bconvention\s+de\s+stage\b",
                    r"\bstage\s+de\s+fin\s+d['’]études\b",
                    r"\bstage\b",
                ]
                if not any(re.search(pat, text_lower) for pat in stage_open_patterns):
                    logger.debug(f"Offre alternance sans mention de stage écartée : {offer.title}")
                    return False

        # 5. Vérification des exclusions de contrat strictes
        for excl in self.strict_exclusion_keywords:
            if excl in text_lower:
                logger.debug(f"Offre exclue ({excl}): {offer.title}")
                return False

        # 6. Filtrage géographique dynamique
        if self.allow_remote and offer.is_remote:
            return True

        if not self.target_locations and not self.target_depts:
            return True

        if offer.department and offer.department in self.target_depts:
            return True

        loc_lower = f"{offer.location} {offer.title} {offer.description}".lower()
        for target in self.target_locations:
            if target in loc_lower:
                return True

        logger.debug(f"Offre hors secteur géographique ({offer.location}): {offer.title}")
        return False

    def filter_offers(self, offers: List[JobOffer]) -> List[JobOffer]:
        """Applique le filtre sur la liste d'offres."""
        retained = [o for o in offers if self.is_eligible(o)]
        logger.info(f"[Filtre] {len(retained)}/{len(offers)} offres éligibles conservées.")
        return retained
