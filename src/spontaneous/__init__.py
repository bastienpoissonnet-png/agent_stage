"""Module de gestion des campagnes de candidatures spontanées locales."""
from .models import TargetCompany, SpontaneousApplication
from .pitch_generator import SpontaneousPitchGenerator
from .mailer import SmtpMailer
from .tracker import SpontaneousTracker

__all__ = [
    "TargetCompany",
    "SpontaneousApplication",
    "SpontaneousPitchGenerator",
    "SmtpMailer",
    "SpontaneousTracker",
]
