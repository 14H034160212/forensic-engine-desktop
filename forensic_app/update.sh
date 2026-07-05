#!/usr/bin/env bash
# Forensic Engine — one-click updater (macOS / Linux).
# Pulls the latest build and overwrites the code, KEEPING your history (runs/) and uploads/.
# Cached Ollama models are untouched. Run:  ./update.sh
set -e
cd "$(dirname "$0")"                     # forensic_app/
ROOT="$(cd .. && pwd)"                   # install root (forensic_app + local_engine)
URL="${UPDATE_SOURCE:-https://forensic-engine.example}/local_deploy.zip"

OLD="$(cat VERSION 2>/dev/null || echo unknown)"
echo "▸ current version: $OLD"
echo "▸ downloading latest from $URL …"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL -H "ngrok-skip-browser-warning: 1" "$URL" -o "$TMP/u.zip"
unzip -q "$TMP/u.zip" -d "$TMP"
SRC="$TMP/local_deploy"
[ -d "$SRC/forensic_app" ] || { echo "✗ bad bundle (no forensic_app)"; exit 1; }

# overwrite code; runs/ + uploads/ are not in the bundle so your data stays put
cp -R "$SRC/forensic_app/." "$ROOT/forensic_app/"
cp -R "$SRC/local_engine/." "$ROOT/local_engine/"
# refresh CLAUDE.md / START-HERE if present
[ -f "$SRC/CLAUDE.md" ] && cp "$SRC/CLAUDE.md" "$ROOT/CLAUDE.md" 2>/dev/null || true
[ -f "$SRC/START-HERE.md" ] && cp "$SRC/START-HERE.md" "$ROOT/START-HERE.md" 2>/dev/null || true
find "$ROOT" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true

NEW="$(cat VERSION 2>/dev/null || echo unknown)"
echo "▸ updated: $OLD  →  $NEW"
echo "▸ restart the app to apply:  ./laptop.sh   (models are cached; startup is fast)"
