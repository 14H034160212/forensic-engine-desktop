#!/usr/bin/env bash
# Forensic Engine — LAPTOP EDITION.
# Runs the whole product locally on a small model. Nothing leaves the laptop.
# One-time: install Ollama (https://ollama.com) and Python 3.9+ with the deps in
# requirements-laptop.txt. Then just: ./laptop.sh
set -e
cd "$(dirname "$0")"
PORT="${PORT:-8800}"

# 1) pick a model tier for THIS machine
RAM_GB=8
case "$(uname -s)" in
  Darwin) RAM_GB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 8589934592) / 1073741824 ));;
  Linux)  RAM_GB=$(( $(awk '/MemTotal/{print $2}' /proc/meminfo) / 1048576 ));;
esac
ARCH="$(uname -m)"
if [ "${FORCE_MODELS:-}" != "" ]; then
  MODELS_ENV="$FORCE_MODELS"
elif [ "$RAM_GB" -ge 16 ] || [ "$ARCH" = "arm64" ]; then
  MODELS_ENV="qwen2.5-coder:7b,llama3.2:3b"      # capable laptop -> 7B (full pincers+arithmetic)
else
  MODELS_ENV="llama3.2:3b"                        # ordinary laptop -> 3B (surface findings)
fi
DEF="${MODELS_ENV%%,*}"
echo "▸ Detected ${RAM_GB}GB RAM, arch ${ARCH}  →  default model: ${DEF}"

# 2) make sure Ollama is up
if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "▸ starting Ollama…"; (ollama serve >/tmp/ollama.log 2>&1 &) ; sleep 4
fi

# 3) pull the model(s) for this tier (first run downloads ~2–4.5GB, then cached)
for m in $(echo "$MODELS_ENV" | tr ',' ' '); do
  echo "▸ ensuring model $m …"; ollama pull "$m" >/dev/null 2>&1 || ollama pull "$m"
done

# 4) run the app locally and open the browser
export MODELS="$MODELS_ENV"
echo "▸ Forensic Engine (laptop) → http://127.0.0.1:${PORT}/   (nothing leaves this machine)"
( sleep 3
  (command -v open  >/dev/null && open  "http://127.0.0.1:${PORT}/") \
  || (command -v xdg-open >/dev/null && xdg-open "http://127.0.0.1:${PORT}/") \
  || true ) >/dev/null 2>&1 &
exec python3 -m uvicorn server:app --host 127.0.0.1 --port "$PORT"
