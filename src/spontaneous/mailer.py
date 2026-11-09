"""Module d'envoi d'emails via SMTP avec mode Dry-Run et temporisation anti-spam."""

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pathlib import Path
import random
import smtplib
import time
from typing import Optional

from config.settings import settings
from src.spontaneous.models import SpontaneousApplication

logger = logging.getLogger("stage_agent.spontaneous.mailer")


class SmtpMailer:
    """Gestionnaire d'envoi SMTP sécurisé avec simulation (Dry-Run) et anti-spam."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.smtp_settings = settings.smtp
        candidates = [
            settings.project_root / "CV_Bastien_Poissonnet.pdf",
            settings.project_root / "cv.pdf",
        ]
        self.cv_path: Path = next((p for p in candidates if p.exists()), candidates[0])

    def send_application(self, app: SpontaneousApplication) -> bool:
        """Envoie une candidature spontanée par email (ou simule l'envoi en dry-run)."""
        logger.info(f"Préparation email pour {app.company_name} <{app.contact_email}>...")

        # Mode simulation (Dry-Run)
        if self.dry_run:
            logger.info(
                f"[DRY-RUN] Email simulé pour {app.company_name} ({app.contact_email}) : "
                f"Objet='{app.subject}' | PJ={'lettre + ' if app.letter_path else ''}{self.cv_path.name if self.cv_path.exists() else 'CV introuvable'}"
            )
            return True

        # Mode envoi réel
        if not self.smtp_settings.is_configured:
            logger.error(
                "Impossible d'envoyer l'email : identifiants SMTP non configurés dans le fichier .env ! "
                "Renseigne SMTP_USER et SMTP_PASSWORD."
            )
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self.smtp_settings.sender_name} <{self.smtp_settings.sender_email}>"
            msg["To"] = app.contact_email
            msg["Subject"] = app.subject

            # Corps du message en texte brut
            msg.attach(MIMEText(app.body, "plain", "utf-8"))

            # Lettre de motivation personnalisée en pièce jointe
            if app.letter_path and Path(app.letter_path).exists():
                with open(app.letter_path, "rb") as f:
                    letter = MIMEApplication(f.read(), _subtype="pdf")
                    letter.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename="Lettre_Motivation_Bastien_Poissonnet.pdf",
                    )
                    msg.attach(letter)

            # Ajout de la pièce jointe cv.pdf si présente
            if self.cv_path.exists():
                with open(self.cv_path, "rb") as f:
                    attach = MIMEApplication(f.read(), _subtype="pdf")
                    attach.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename="CV_Bastien_Poissonnet_BUT_Data_IA.pdf",
                    )
                    msg.attach(attach)

            # Connexion au serveur SMTP (SSL ou STARTTLS selon port)
            if self.smtp_settings.port == 465:
                server = smtplib.SMTP_SSL(self.smtp_settings.host, self.smtp_settings.port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_settings.host, self.smtp_settings.port, timeout=15)
                server.starttls()

            server.login(self.smtp_settings.user, self.smtp_settings.password)
            server.send_message(msg)
            server.quit()

            logger.info(f"[ENVOI RÉEL RÉUSSI] Email transmis à {app.company_name} ({app.contact_email})")

            # Temporisation aléatoire anti-spam entre deux envois
            delay = random.uniform(self.smtp_settings.delay_min, self.smtp_settings.delay_max)
            logger.info(f"Temporisation anti-spam : pause de {delay:.1f} secondes...")
            time.sleep(delay)
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du mail à {app.company_name} : {e}")
            return False

