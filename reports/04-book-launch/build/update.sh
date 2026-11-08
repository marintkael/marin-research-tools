#!/usr/bin/env bash
# Bericht 04 – Aktualisierung. Aufruf aus beliebigem Ordner:
#   build/update.sh                 Ankertag: Grundlinie prüfen/nachtragen, laufenden Abzug ziehen, Auswertung + Abbildungen
#   build/update.sh effect-freeze   einmalig ab 08.11.2026: Wirkungsfenster einfrieren (Stichtag 07.11.2026 23:59:59 UTC)
#   build/update.sh observe-freeze  einmalig ab 07.01.2027: Beobachtungsfenster einfrieren (Stichtag 06.01.2027 23:59:59 UTC)
# Voraussetzung: MARIN_D1_CMD (oder CF_ACCOUNT_ID, D1_DATABASE_ID, CF_API_TOKEN) gesetzt; PYTHON optional.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
if [ -z "${MARIN_D1_CMD:-}" ] && [ -z "${CF_API_TOKEN:-}" ]; then echo "Zugang fehlt: MARIN_D1_CMD setzen" >&2; exit 2; fi
freeze_once () {   # $1 Ordner, $2 Stichtag
  if [ -e "data/$1/freeze.json" ]; then echo "data/$1 existiert bereits – wird nicht überschrieben" >&2; exit 3; fi
  "$PY" build/fetch.py --cutoff "$2" --out "data/$1"
}
case "${1:-anchor}" in
  anchor)         "$PY" build/freeze_baseline.py; "$PY" build/fetch.py --out data/current ;;
  effect-freeze)  freeze_once effect_freeze 2026-11-07T23:59:59Z ;;
  observe-freeze) freeze_once observation_freeze 2027-01-06T23:59:59Z ;;
  *) echo "unbekannter Modus: $1" >&2; exit 2 ;;
esac
# 08.11.2026: ein Aufruf rechnet Hauptanalyse, Sensitivitäten (Bewertungsregeln 02.11., leere Antworten, ohne Änderung 4)
# und die nicht vorregistrierte Erweiterung bis 08.11. → data/results*.json (README_BUILD, Nachtrag 08.11.)
"$PY" build/analyze.py
"$PY" build/figures.py
