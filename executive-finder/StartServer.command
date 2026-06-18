#!/bin/bash
# Executive Finder – Server starten
# Doppelklick auf diese Datei startet den Server

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "  Executive Finder – Server startet..."
echo "========================================"
echo ""

# Python prüfen
if ! command -v python3 &>/dev/null; then
  echo "FEHLER: Python3 nicht gefunden."
  echo "Bitte Python unter https://python.org herunterladen."
  read -p "Enter drücken zum Schließen..."
  exit 1
fi

# Pakete installieren falls nötig
echo "Prüfe Pakete..."
pip3 install -q -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null

echo ""
echo "Server läuft auf: http://localhost:8000"
echo "Browser öffnen mit: http://localhost:8000"
echo ""
echo "Zum Stoppen: CMD+C drücken"
echo "========================================"
echo ""

# Browser nach 2 Sekunden öffnen
(sleep 2 && open "http://localhost:8000") &

# Server starten
cd "$SCRIPT_DIR"
python3 run.py
