"""Module d'envoi d'emails via SMTP avec mode Dry-Run, temporisation anti-spam et lien mailto."""

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pathlib import Path
import random
import re
import smtplib
import time
from urllib.parse import quote

from config.settings import settings
from src.spontaneous.models import SpontaneousApplication

logger = logging.getLogger("stage_agent.spontaneous.mailer")


class SmtpMailer:
    """Gestionnaire d'envoi SMTP sécurisé avec simulation (Dry-Run) et anti-spam."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.smtp_settings = settings.smtp
        self.cv_path: Path = settings.cv_path

    @staticmethod
    def _safe_candidate_slug() -> str:
        raw = settings.candidate_name.strip() or "Candidat"
        return re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_") or "Candidat"

    @staticmethod
    def build_mailto_url(app: SpontaneousApplication) -> str:
        """Construit un lien mailto: pré-rempli pour ouvrir un brouillon dans la messagerie locale."""
        subject = quote(app.subject, safe="")
        body = quote(app.body, safe="")
        to = quote(app.contact_email.strip(), safe="@.")
        return f"mailto:{to}?subject={subject}&body={body}"

    def send_application(self, app: SpontaneousApplication) -> bool:
        """Envoie une candidature spontanée par email (ou simule l'envoi en dry-run)."""
        logger.info(f"Préparation email pour {app.company_name} <{app.contact_email}>...")
        self.cv_path = settings.cv_path

        if self.dry_run:
            logger.info(
                f"[DRY-RUN] Email simulé pour {app.company_name} ({app.contact_email}) : "
                f"Objet='{app.subject}' | PJ={'lettre + ' if app.letter_path else ''}{self.cv_path.name if self.cv_path.exists() else 'CV introuvable'}"
            )
            return True

        if not self.smtp_settings.is_configured:
            logger.error(
                "Impossible d'envoyer l'email : identifiants SMTP non configurés dans le fichier .env ! "
                "Renseigne SMTP_USER et SMTP_PASSWORD."
            )
            return False

        try:
            slug = self._safe_candidate_slug()
            sender_name = self.smtp_settings.sender_name or settings.candidate_name or self.smtp_settings.user
            sender_email = self.smtp_settings.sender_email or self.smtp_settings.user

            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = app.contact_email
            msg["Subject"] = app.subject
            msg.attach(MIMEText(app.body, "plain", "utf-8"))

            if app.letter_path and Path(app.letter_path).exists():
                with open(app.letter_path, "rb") as f:
                    letter = MIMEApplication(f.read(), _subtype="pdf")
                    letter.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=f"Lettre_Motivation_{slug}.pdf",
                    )
                    msg.attach(letter)

            if self.cv_path.exists():
                with open(self.cv_path, "rb") as f:
                    attach = MIMEApplication(f.read(), _subtype="pdf")
                    attach.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=f"CV_{slug}.pdf",
                    )
                    msg.attach(attach)

            if self.smtp_settings.port == 465:
                server = smtplib.SMTP_SSL(self.smtp_settings.host, self.smtp_settings.port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_settings.host, self.smtp_settings.port, timeout=15)
                server.starttls()

            server.login(self.smtp_settings.user, self.smtp_settings.password)
            server.send_message(msg)
            server.quit()

            logger.info(f"[ENVOI RÉEL RÉUSSI] Email transmis à {app.company_name} ({app.contact_email})")
            delay = random.uniform(self.smtp_settings.delay_min, self.smtp_settings.delay_max)
            logger.info(f"Temporisation anti-spam : pause de {delay:.1f} secondes...")
            time.sleep(delay)
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du mail à {app.company_name} : {e}")
            return False
