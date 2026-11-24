#!/bin/bash

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
mkdir -p "$DIR/logs"

if [ ! -x "$DIR/.venv/bin/streamlit" ]; then
  echo "L'application n'est pas encore installee. Lancement de l'installation..."
  "$DIR/Installer_Mac.command"
  exit $?
fi

if curl -sf "http://localhost:8501" >/dev/null 2>&1; then
  open "http://localhost:8501"
  exit 0
fi

nohup "$DIR/.venv/bin/streamlit" run "$DIR/app.py" \
  --server.headless true \
  --browser.gatherUsageStats false \
  > "$DIR/logs/streamlit.log" 2>&1 &

for i in $(seq 1 20); do
  if curl -sf "http://localhost:8501" >/dev/null 2>&1; then
    open "http://localhost:8501"
    exit 0
  fi
  sleep 1
done

open "http://localhost:8501"
