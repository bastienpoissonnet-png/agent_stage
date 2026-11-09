"""Générateur d'emails de motivation spontanés ultra-personnalisés selon le secteur."""

import logging
from config.settings import settings
from src.spontaneous.models import SpontaneousApplication, TargetCompany

logger = logging.getLogger("stage_agent.spontaneous.pitch")


class SpontaneousPitchGenerator:
    """Génère un email percutant adapté à l'activité spécifique de l'entreprise cible."""

    def __init__(self):
        self.candidate = settings.profile.get("candidate", {})
        self.search = settings.profile.get("search_criteria", {})

    def generate_application(self, company: TargetCompany) -> SpontaneousApplication:
        """Produit un objet SpontaneousApplication avec objet et corps de mail rédigé."""
        sector_lower = company.sector.lower()
        dept = company.department
        city = company.city

        # 1. Accroche géographique contextualisée
        if dept == "17" or "rochelle" in city.lower():
            geo_hook = (
                "Étant actuellement étudiant à l'IUT de La Rochelle et familier de l'écosystème local, "
                "rejoindre vos équipes sur le bassin rochelais serait une opportunité privilégiée."
            )
        elif dept == "79" or "niort" in city.lower():
            geo_hook = (
                "Conscient de l'expertise de premier plan développée sur le pôle technologique et décisionnel niortais, "
                "je souhaite m'investir sur site pour contribuer à vos projets."
            )
        elif dept == "85" or "yon" in city.lower():
            geo_hook = (
                "Originaire de Vendée, je suis particulièrement attentif aux dynamiques d'innovation du territoire "
                "et disponible immédiatement pour intervenir dans vos locaux."
            )
        elif dept in ("75", "92", "93", "94") or "paris" in city.lower():
            geo_hook = (
                "Je serai pleinement mobile et présent en région parisienne pour toute la durée de mon stage."
            )
        else:
            geo_hook = f"Je suis disponible pour intervenir en présentiel ou hybride au sein de vos locaux à {city}."

        # 2. Angle technique selon le secteur d'activité
        if any(w in sector_lower for w in ["assurance", "mutuelle", "finance"]):
            tech_angle = (
                "Votre secteur manipule des flux de données critiques où la qualité, la traçabilité et l'exploitation des données "
                "sont stratégiques. Formé aux pipelines de données (Python, SQL), à la modélisation et à l'intelligence artificielle, "
                "je souhaite mettre en pratique ces compétences au service de vos cas d'usage métiers."
            )
        elif any(w in sector_lower for w in ["éditeur", "saas", "logiciel", "crm", "erp"]):
            tech_angle = (
                "Mon expérience précédente de développeur chez Orisha (éditeur européen de progiciels SaaS) m'a permis d'appréhender "
                "concrètement les exigences d'un cycle de développement logiciel en équipe (méthode agile/SCRUM, rigueur du code, tests). "
                "J'ai également manipulé Elasticsearch et des bases de données relationnelles pour optimiser la recherche et le traitement d'informations."
            )
        elif any(w in sector_lower for w in ["conseil", "esn", "services numériques"]):
            tech_angle = (
                "Polyvalent et curieux, je maîtrise aussi bien l'ingénierie des données (Python, SQL) que le développement logiciel (Rust, C++, React). "
                "Mon passage chez un éditeur de logiciels SaaS (Orisha) m'a habitué à m'adapter rapidement à de nouveaux environnements et à travailler en méthode agile/SCRUM."
            )
        elif any(w in sector_lower for w in ["ia", "data", "science"]):
            tech_angle = (
                "Passionné par l'exploitation des données et le déploiement de modèles d'IA, je concentre mes projets sur l'apprentissage automatique, "
                "le traitement de données volumineuses et le développement Python de bout en bout."
            )
        else:
            tech_angle = (
                "Mes compétences couvrent l'ingénierie des données, le développement d'outils Python et l'intégration de modèles d'IA, "
                "avec une rigueur renforcée par mon expérience en développement chez Orisha (éditeur de logiciels SaaS)."
            )

        # 3. Objet de mail clair et percutant
        subject = f"Candidature Stage BUT 3 Data & IA (22 mars - fin juin 2027) — Bastien Poissonnet"

        # 4. Corps de texte professionnel
        body = (
            f"Madame, Monsieur,\n\n"
            f"Actuellement en 3ème année de BUT Informatique à l'IUT de La Rochelle, spécialisé en Data et Intelligence Artificielle, "
            f"je me permets de vous soumettre ma candidature spontanée pour un stage de fin d'études de 14 à 15 semaines, "
            f"du 22 mars 2027 à fin juin 2027.\n\n"
            f"L'expertise de {company.name} dans le domaine ({company.sector}) a particulièrement retenu mon attention. {geo_hook}\n\n"
            f"{tech_angle}\n\n"
            f"Rigoureux, doté d'un bon esprit d'équipe et d'une solide capacité d'adaptation, je suis prêt à m'investir concrètement au sein de votre équipe technique.\n\n"
            f"Je serais honoré d'échanger avec vous lors d'un entretien pour vous exposer plus en détail mes motivations et cerner vos besoins actuels. "
            f"Mon CV détaillé est joint à ce message.\n\n"
            f"Dans l'attente de votre retour, je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.\n\n"
            f"{self.candidate.get('name', 'Bastien Poissonnet')}\n"
            f"Étudiant en 3ème année BUT Informatique (Data & IA) — IUT de La Rochelle\n"
            f"📞 {self.candidate.get('phone', '06 01 46 18 43')} | ✉️ {self.candidate.get('email', 'bastien.poissonnet@gmail.com')}"
        )

        return SpontaneousApplication(
            company_name=company.name,
            city=company.city,
            contact_email=company.contact_email,
            subject=subject,
            body=body,
            status="Prêt à envoyer",
            notes=company.context_note,
        )
