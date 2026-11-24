"""Génère une archive ZIP propre pour un autre utilisateur sur Mac (sans données personnelles)."""

import csv
from pathlib import Path
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.spontaneous.tracker import SpontaneousTracker
from src.storage.tracker_csv import CsvTracker

OUTPUT_ZIP = PROJECT_ROOT / "StageAgent_Pour_Mac.zip"
ROOT_PREFIX = "StageAgent"

FILES_TO_COPY = [
    "app.py",
    "main.py",
    "run_daily.py",
    "requirements.txt",
    ".env.example",
    "launch_ui.bat",
    "Installer_Mac.command",
    "Lancer_Mac.command",
    "GUIDE_INSTALLATION_MAC.md",
    "README.md",
    "config/__init__.py",
    "config/settings.py",
    "config/profile.example.json",
    "data/lettre_type.example.txt",
]

EXECUTABLE_SCRIPTS = {"Installer_Mac.command", "Lancer_Mac.command"}


def _add_bytes(zf: zipfile.ZipFile, arcname: str, data: bytes, executable: bool = False) -> None:
    info = zipfile.ZipInfo(arcname)
    mode = 0o755 if executable else 0o644
    info.external_attr = (mode & 0xFFFF) << 16
    zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)


def build_mac_zip() -> Path:
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Fichiers individuels du cœur de l'application
        for rel in FILES_TO_COPY:
            src = PROJECT_ROOT / rel
            if not src.exists():
                raise FileNotFoundError(f"Fichier manquant pour l'export Mac : {src}")
            raw = src.read_bytes()
            is_exec = rel in EXECUTABLE_SCRIPTS
            if is_exec:
                # Forcer les fins de ligne LF pour macOS
                raw = raw.replace(b"\r\n", b"\n")
            _add_bytes(zf, f"{ROOT_PREFIX}/{rel}", raw, executable=is_exec)

        # 2. Code source Python sous src/
        for py_file in sorted((PROJECT_ROOT / "src").rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            rel = py_file.relative_to(PROJECT_ROOT).as_posix()
            _add_bytes(zf, f"{ROOT_PREFIX}/{rel}", py_file.read_bytes())

        # 3. Initialiser les fichiers génériques vierges (aucune donnée personnelle de Bastien)
        profile_example = (PROJECT_ROOT / "config/profile.example.json").read_bytes()
        _add_bytes(zf, f"{ROOT_PREFIX}/config/profile.json", profile_example)

        lettre_example = (PROJECT_ROOT / "data/lettre_type.example.txt").read_bytes()
        _add_bytes(zf, f"{ROOT_PREFIX}/data/lettre_type.txt", lettre_example)

        # Modèle vierge d'entreprises cibles
        companies_csv = (
            "Nom,Ville,Departement,Secteur,Site_Web,Email_Contact,Note_Contexte\n"
            "Exemple Entreprise,Paris,75,Communication / Digital,https://exemple.fr,recrutement@exemple.fr,Adresse à vérifier avant envoi.\n"
        ).encode("utf-8")
        _add_bytes(zf, f"{ROOT_PREFIX}/data/target_companies.csv", companies_csv)

        # Tableaux de suivi vides (UTF-8 BOM pour Excel)
        offers_header = (",".join(CsvTracker.FIELDNAMES) + "\n").encode("utf-8-sig")
        _add_bytes(zf, f"{ROOT_PREFIX}/candidatures.csv", offers_header)

        spont_header = (",".join(SpontaneousTracker.FIELDNAMES) + "\n").encode("utf-8-sig")
        _add_bytes(zf, f"{ROOT_PREFIX}/suivi_spontanees.csv", spont_header)

    return OUTPUT_ZIP


if __name__ == "__main__":
    out = build_mac_zip()
    print(f"Archive Mac generee : {out} ({out.stat().st_size} octets)")
