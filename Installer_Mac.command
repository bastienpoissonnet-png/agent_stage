#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=================================================="
echo "   Installation de Stage Agent sur Mac"
echo "=================================================="
echo ""

# Recherche d'un vrai Python 3.9+ (sans déclencher le stub Apple /usr/bin/python3)
PYTHON_BIN=""
CANDIDATES=(
  /opt/homebrew/bin/python3
  /Library/Frameworks/Python.framework/Versions/Current/bin/python3
  /Library/Frameworks/Python.framework/Versions/3.*/bin/python3
  /usr/local/bin/python3
)
if xcode-select -p >/dev/null 2>&1; then
  CANDIDATES+=("$(command -v python3 2>/dev/null || true)")
fi

for cand in "${CANDIDATES[@]}"; do
  if [ -n "$cand" ] && [ -x "$cand" ]; then
    if "$cand" -c "import sys; assert sys.version_info >= (3, 9)" >/dev/null 2>&1; then
      PYTHON_BIN="$cand"
      break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "[ERREUR] Python 3.9 ou plus recent n'est pas installe sur ce Mac."
  echo "La page officielle de telechargement va s'ouvrir dans votre navigateur."
  echo "Installez le fichier .pkg propose, puis relancez Installer_Mac.command."
  open "https://www.python.org/downloads/macos/"
  read -r -p "Appuyez sur Entree pour fermer..."
  exit 1
fi

echo "Python detecte : $PYTHON_BIN"
mkdir -p "$DIR/logs" "$DIR/letters" "$DIR/data"

if [ ! -d "$DIR/.venv" ]; then
  echo "Creation de l'environnement isole (.venv)..."
  "$PYTHON_BIN" -m venv "$DIR/.venv"
fi

echo "Installation des bibliotheques (cela peut prendre 1 a 2 minutes la premiere fois)..."
"$DIR/.venv/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
"$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt"

if [ ! -f "$DIR/config/profile.json" ] && [ -f "$DIR/config/profile.example.json" ]; then
  cp "$DIR/config/profile.example.json" "$DIR/config/profile.json"
fi

if [ ! -f "$DIR/data/lettre_type.txt" ] && [ -f "$DIR/data/lettre_type.example.txt" ]; then
  cp "$DIR/data/lettre_type.example.txt" "$DIR/data/lettre_type.txt"
fi

chmod +x "$DIR/Installer_Mac.command" "$DIR/Lancer_Mac.command"

# Creation d'une application Bureau sans fenetre Terminal persistante
APP_DIR="$HOME/Desktop/Stage Agent.app"
mkdir -p "$APP_DIR/Contents/MacOS"

cat > "$APP_DIR/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>StageAgent</string>
  <key>CFBundleIdentifier</key>
  <string>local.stageagent.launcher</string>
  <key>CFBundleName</key>
  <string>Stage Agent</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
EOF

cat > "$APP_DIR/Contents/MacOS/StageAgent" << EOF
#!/bin/bash
nohup "$DIR/Lancer_Mac.command" >/dev/null 2>&1 &
EOF
chmod +x "$APP_DIR/Contents/MacOS/StageAgent"

echo ""
echo "=================================================="
echo "   Installation terminee !"
echo "   Un raccourci 'Stage Agent' a ete cree sur votre Bureau."
echo "=================================================="
echo ""
echo "Ouverture de Stage Agent dans votre navigateur..."
"$DIR/Lancer_Mac.command"
