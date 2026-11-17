"""Générateur d'e-mails d'accompagnement pour les candidatures spontanées.

Le fond de la candidature est porté par la lettre de motivation PDF personnalisée
(src/letters). Le mail reste court et factuel.
"""

import logging
from config.settings import settings
from src.spontaneous.models import SpontaneousApplication, TargetCompany

logger = logging.getLogger("stage_agent.spontaneous.pitch")


class SpontaneousPitchGenerator:
    """Génère l'objet et le corps du mail d'accompagnement."""

    def __init__(self):
        self.candidate = settings.profile.get("candidate", {})

    def generate_application(self, company: TargetCompany) -> SpontaneousApplication:
        subject = "Candidature spontanée – Stage BUT Informatique DATA/IA (22 mars - 25 juin 2027) – Bastien Poissonnet"

        body = (
            "Madame, Monsieur,\n\n"
            "Étudiant en 3ème année de BUT Informatique (spécialité DATA/IA) à l'IUT de La Rochelle, site de Niort, "
            f"je vous adresse ma candidature spontanée pour un stage de 14 semaines, du 22 mars au 25 juin 2027, au sein de {company.name}.\n\n"
            "Vous trouverez ci-joints ma lettre de motivation et mon CV. "
            "Je reste disponible pour échanger par téléphone ou en visio.\n\n"
            "Cordialement,\n"
            f"{self.candidate.get('name', 'Bastien Poissonnet')}\n"
            f"{self.candidate.get('phone', '')} | {self.candidate.get('email', '')}"
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

    def generate_followup(
        self,
        company_name: str,
        city: str,
        contact_email: str,
        sent_date: str,
        notes: str = "",
    ) -> SpontaneousApplication:
        """Génère l'e-mail de relance à J+7 pour une candidature déjà envoyée."""
        subject = "Relance – Candidature Stage BUT Informatique DATA/IA (22 mars - 25 juin 2027) – Bastien Poissonnet"
        body = (
            "Madame, Monsieur,\n\n"
            f"Je me permets de revenir vers vous suite à ma candidature spontanée envoyée le {sent_date} "
            f"pour un stage de 14 semaines en 3ème année de BUT Informatique (spécialité DATA/IA, du 22 mars au 25 juin 2027) au sein de {company_name}.\n\n"
            "Toujours très motivé à l'idée de rejoindre votre équipe, je vous joins à nouveau ma lettre de motivation et mon CV. "
            "Je reste à votre disposition pour échanger par téléphone ou en visio.\n\n"
            "Cordialement,\n"
            f"{self.candidate.get('name', 'Bastien Poissonnet')}\n"
            f"{self.candidate.get('phone', '')} | {self.candidate.get('email', '')}"
        )
        return SpontaneousApplication(
            company_name=company_name,
            city=city,
            contact_email=contact_email,
            subject=subject,
            body=body,
            status="Relance prête",
            notes=notes,
        )
