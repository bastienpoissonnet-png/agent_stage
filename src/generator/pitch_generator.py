"""Générateur de messages d'accroche ultra-personnalisés pour chaque offre."""

import logging
from config.settings import settings
from src.models import JobOffer

logger = logging.getLogger("stage_agent.generator.pitch")


class PitchGenerator:
    """Rédige un message d'accroche percutant et contextuel pour chaque entreprise."""

    def __init__(self):
        self.candidate = settings.profile.get("candidate", {})
        self.search = settings.profile.get("search_criteria", {})

    def generate_pitch(self, offer: JobOffer) -> str:
        """Produit un pitch personnalisé selon l'entreprise, le poste et la stack demandée."""
        company = offer.company if offer.company != "Confidentiel / Non spécifié" else "votre équipe"
        title = offer.title

        # Analyse des compétences communes
        skills_str = ", ".join(offer.detected_skills) if offer.detected_skills else "Python et Data"

        # Contexte selon les technos clés
        tech_hook = ""
        if "Elasticsearch" in offer.detected_skills:
            tech_hook = "avec une attention particulière portée sur la recherche et l'indexation de données via Elasticsearch"
        elif "Data / IA" in offer.detected_skills:
            tech_hook = "avec un fort intérêt pour le traitement de données et l'implémentation de modèles d'IA"
        elif "Python" in offer.detected_skills:
            tech_hook = "orienté développement d'outils et pipelines Python robustes"
        else:
            tech_hook = "au sein de votre environnement technique"

        # Contexte localisation / mobilité
        loc_hook = ""
        if "rochelle" in offer.location.lower():
            loc_hook = "Étant actuellement étudiant à l'IUT de La Rochelle, je suis immédiatement disponible sur le bassin rochelais."
        elif "yon" in offer.location.lower() or offer.department == "85":
            loc_hook = "Originaire de Vendée, je connais parfaitement le dynamisme économique de La Roche-sur-Yon et ses environs."
        elif "niort" in offer.location.lower() or offer.department == "79":
            loc_hook = "Le pôle technologique niortais correspond exactement à mon projet professionnel."
        elif "paris" in offer.location.lower() or offer.department in ["75", "92", "93", "94"]:
            loc_hook = "Je suis pleinement mobile en région parisienne pour toute la durée du stage."
        elif offer.is_remote:
            loc_hook = "Habitué au travail autonome et collaboratif, le format télétravail/hybride s'intègre parfaitement à mon organisation."

        pitch = (
            f"Bonjour,\n\n"
            f"Actuellement en 3ème année de BUT Informatique à l'IUT de La Rochelle (spécialité Data & Intelligence Artificielle), "
            f"je me permets de vous contacter au sujet de votre offre de {title} au sein de {company}.\n\n"
            f"À la recherche de mon stage de fin d'études du 22 mars 2027 à fin juin 2027 (14 à 15 semaines), votre opportunité a immédiatement retenu mon attention, "
            f"notamment en raison des technologies mobilisées ({skills_str}) {tech_hook}.\n\n"
            f"Lors de mon expérience en tant que développeur chez Orisha (éditeur européen de logiciels de gestion SaaS), "
            f"j'ai pu consolider ma rigueur de développement en environnement agile/SCRUM et mon goût pour la conception de solutions logicielles performantes. "
            f"{loc_hook}\n\n"
            f"Je serais ravi d'échanger 10 à 15 minutes par téléphone ou visio pour vous présenter plus en détail mon parcours et voir comment je peux contribuer à vos projets en cours.\n\n"
            f"Bien cordialement,\n"
            f"{self.candidate.get('name', 'Bastien Poissonnet')}\n"
            f"📞 {self.candidate.get('phone', '06 01 46 18 43')} | ✉️ {self.candidate.get('email', 'bastien.poissonnet@gmail.com')}"
        )

        return pitch

    def enrich_offers(self, offers: list) -> list:
        """Génère le pitch pour chaque offre filtrée."""
        for offer in offers:
            offer.personalized_pitch = self.generate_pitch(offer)
        return offers
