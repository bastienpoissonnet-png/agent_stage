"""Veille quotidienne : lance le scan, journalise le résultat et résume les nouvelles offres.

Conçu pour être lancé par le Planificateur de tâches Windows (voir scripts/register_daily_task.ps1).
Ne postule à rien : il prépare uniquement offres + lettres PDF + tableau de suivi.
"""

import logging
from datetime import datetime
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)  # le planificateur démarre dans System32 par défaut
sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"veille_{datetime.now():%Y-%m-%d}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8")],
)
log = logging.getLogger("stage_agent.daily")


def main() -> int:
    try:
        from main import run_job_search
        from config.settings import settings

        log.info("=== Début de la veille quotidienne ===")
        new_offers = run_job_search(source_filter="all", min_score=settings.min_score_threshold,
                                    limit=settings.max_offers_per_source)
        summary = ROOT / "logs" / "derniere_veille.txt"
        lines = [f"Veille du {datetime.now():%d/%m/%Y à %H:%M} : {len(new_offers)} nouvelle(s) offre(s)"]
        lines += [f"- [{o.score}] {o.title} | {o.company} | {o.location} | {o.url}" for o in new_offers]
        summary.write_text("\n".join(lines), encoding="utf-8")
        log.info(lines[0])
        log.info("=== Fin de la veille ===")
        return 0
    except Exception:
        log.exception("La veille quotidienne a échoué")
        return 1


if __name__ == "__main__":
    sys.exit(main())
