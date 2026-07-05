# Forensic Engine — Laptop Edition

Runs the whole product **locally on your laptop**, on a small local model. Nothing leaves
the machine — no server, no internet needed after setup.

🇨🇳 中文版见 [LAPTOP.zh.md](LAPTOP.zh.md).

## One-time setup
1. Install **Ollama**: https://ollama.com  (Mac / Windows / Linux — all native)
2. Install Python 3.9+ and deps:  `pip install -r requirements-laptop.txt`

## Run

**macOS / Linux**
```bash
./laptop.sh
```

**Windows** — double-click `laptop.bat`, or in PowerShell / CMD:
```bat
laptop.bat
```

The launcher auto-detects your machine, picks a suitable model, downloads it on first run
(~2–4.5 GB, then cached), starts the app, and opens your browser at
http://127.0.0.1:8800/.

- **Ordinary laptop (CPU, 8–16 GB):** defaults to a 3B model — fast to run, surfaces the
  issues + the full deterministic arithmetic red flags, lighter on the deepest structural
  findings.
- **Apple Silicon (16 GB+) or a laptop with a GPU:** defaults to a 7B model — the full
  analysis (structural “pincers” + unit-economics), still local.
- Force a model:  `FORCE_MODELS="llama3.2:3b" ./laptop.sh`  (Windows: `set FORCE_MODELS=llama3.2:3b` then `laptop.bat`)

## Manual start (any OS, no launcher)
```bash
ollama pull llama3.2:3b
# macOS / Linux:
MODELS="llama3.2:3b,qwen2.5-coder:7b" python3 -m uvicorn server:app --host 127.0.0.1 --port 8800
```
```powershell
# Windows PowerShell:
$env:MODELS="llama3.2:3b,qwen2.5-coder:7b"; python -m uvicorn server:app --host 127.0.0.1 --port 8800
```

## Updating
The app does **not** auto-update — it's a local copy. To get the latest build:
- **macOS / Linux:** `./update.sh`  ·  **Windows:** `update.bat`
It pulls the newest code, **keeps your history (`runs/`) and uploads**, and leaves cached
Ollama models untouched (so it's fast). Restart with `laptop.sh` / `laptop.bat` afterwards.
The app also checks on start-up and shows a banner when a newer version is available (needs a
network connection for that check; it's silent when offline).

## Notes
- **PDF export (weasyprint)** is optional and hard to install on Windows (needs GTK libs).
  Leave it out — everything else works, and export falls back to printable HTML.
- Everything runs against your local Ollama; the engine never calls the web (except the
  optional update check above).
