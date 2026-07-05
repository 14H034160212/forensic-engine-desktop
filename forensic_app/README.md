# Forensic Engine — Forensic Engine (web app)

A real, usable application that runs the **blind two-pass forensic prosecution + unit-economics**
engine on a pitch deck. Upload a PDF/Word deck → the engine runs **live on your own hardware** →
a polished, interactive report. Plus cross-document conflict detection, run history, and PDF export.

**Private by architecture:** every model call goes to a local Ollama daemon. No web access,
no third-party API, nothing leaves the machine.

---

## Quick start

```bash
cd forensic_app
./start.sh                      # → http://127.0.0.1:8800/
# or:  python3 -m uvicorn server:app --host 127.0.0.1 --port 8800
```

Open **http://127.0.0.1:8800/**, drop in a deck (or click a built-in sample), pick a model, hit **Run**.

### Private remote demo (no public exposure)
The app binds to localhost. To show it from a laptop, SSH-tunnel the port:
```bash
ssh -L 8800:127.0.0.1:8800 <user>@<this-server>
# then open http://127.0.0.1:8800/ on the laptop
```

---

## What it does

- **New analysis** — upload PDF / DOCX / paste text → streaming live run → interactive report
  (pipeline counts, the **arithmetic red flags computed from the deck's own numbers**, Pass-2
  structural "pincer" contradictions, ranked register, blind predictive verdict).
- **Cross-document** — upload 2+ documents → find claims that cannot both be true (pure internal
  logic; works on confidential material with nothing to look up online).
- **History** — every run is saved; reopen, export, or delete.
- **Export PDF** — one click, server-rendered.

## Models (local, selectable per run)
- `qwen2.5-coder:32b` — fast (~100s), good default for a live demo
- `L3370B:latest` (Llama 3.3 70B) — better calibrated, ~5 min, for the formal result
- `deepseek-r1:32b` — reasoning

## Notes
- Built-in sample decks (QuickBite, QuickBite) load with one click for a no-friction demo.
- Confidential — decision-support, not legal/financial advice. Do not deploy to a public URL.

## Layout
```
forensic_app/
  server.py        FastAPI backend (upload, streaming run, cross-doc, history, export)
  parsing.py       PDF / DOCX / TXT → text
  static/index.html  the web UI
  runs/            saved run history (JSON)
  start.sh         one-click launch
engine: ../local_engine/prosecution_engine.py
```
