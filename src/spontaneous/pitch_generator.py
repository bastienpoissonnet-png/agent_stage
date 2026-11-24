"""Générateur d'e-mails d'accompagnement dynamiques pour les candidatures spontanées."""

import logging
from config.settings import settings
from src.spontaneous.models import SpontaneousApplication, TargetCompany

logger = logging.getLogger("stage_agent.spontaneous.pitch")


class SpontaneousPitchGenerator:
    """Génère l'objet et le corps du mail d'accompagnement à partir du profil."""

    @staticmethod
    def _profile_fields():
        candidate = settings.profile.get("candidate", {})
        search = settings.profile.get("search_criteria", {})
        name = candidate.get("name", "").strip() or "Candidat"
        degree = candidate.get("degree", "").strip() or "Formation"
        specialty = candidate.get("specialty", "").strip()
        school = candidate.get("school", "").strip()
        period = search.get("internship_period", "").strip()
        phone = candidate.get("phone", "").strip()
        email = candidate.get("email", "").strip()
        return name, degree, specialty, school, period, phone, email

    def generate_application(self, company: TargetCompany) -> SpontaneousApplication:
        name, degree, specialty, school, period, phone, email = self._profile_fields()
        spec_part = f" (spécialité {specialty})" if specialty else ""
        school_part = f" à {school}" if school else ""
        period_part = f" ({period})" if period else ""
        contact_line = " | ".join(x for x in (phone, email) if x)

        subject = f"Candidature spontanée – Stage {degree}{period_part} – {name}"
        body = (
            "Madame, Monsieur,\n\n"
            f"Étudiant(e) en {degree}{spec_part}{school_part}, "
            f"je vous adresse ma candidature spontanée pour un stage{period_part} au sein de {company.name}.\n\n"
            "Vous trouverez ci-joints ma lettre de motivation et mon CV. "
            "Je reste disponible pour échanger par téléphone ou en visio.\n\n"
            "Cordialement,\n"
            f"{name}"
            + (f"\n{contact_line}" if contact_line else "")
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
        name, degree, specialty, school, period, phone, email = self._profile_fields()
        spec_part = f" (spécialité {specialty})" if specialty else ""
        period_part = f" ({period})" if period else ""
        contact_line = " | ".join(x for x in (phone, email) if x)

        subject = f"Relance – Candidature Stage {degree}{period_part} – {name}"
        body = (
            "Madame, Monsieur,\n\n"
            f"Je me permets de revenir vers vous suite à ma candidature spontanée envoyée le {sent_date} "
            f"pour un stage en {degree}{spec_part}{period_part} au sein de {company_name}.\n\n"
            "Toujours très motivé(e) à l'idée de rejoindre votre équipe, je vous joins à nouveau ma lettre de motivation et mon CV. "
            "Je reste à votre disposition pour échanger par téléphone ou en visio.\n\n"
            "Cordialement,\n"
            f"{name}"
            + (f"\n{contact_line}" if contact_line else "")
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
