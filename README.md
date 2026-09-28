# Forensic Engine — desktop / local build

A blind, fully-local document reasoning engine with a web UI. Upload a document → a multi-pass
reasoning-excavation + deterministic unit-economics engine runs entirely on local hardware
(via [Ollama](https://ollama.com)) → an interactive report. **Nothing leaves the machine.**

## Run from source
```bash
cd forensic_app
pip install -r requirements-laptop.txt
./laptop.sh          # macOS/Linux   ·   laptop.bat on Windows
```
Opens http://127.0.0.1:8800/. Requires Ollama running locally.

## Native app (zero-Python for end users)
See [`forensic_app/desktop/`](forensic_app/desktop/) — PyInstaller single-binary build
(`build.sh`/`build.bat`) and a Tauri scaffold for signed installers. CI builds all three OSes:
[`.github/workflows/build-desktop.yml`](.github/workflows/build-desktop.yml).

## Learning DRE (Tarski Deep Reasoning Engine)
The same shell hosts a second application of the deep-reasoning core: the **Learning report engine**
(nav → *Learning DRE*). Give it one recorded learning **Episode** (a Tarski Telemetry event stream)
and it reasons over that verifiable evidence against the **Canonical Taxonomy of Learning
Capabilities**, returning a selective Teacher report + Student reflection and preserving the full
internal consideration for audit. It shares the app's local Ollama — no extra runtime — and ships with
the full Canonical Taxonomy of Learning Capabilities v3.1 (137 constructs / 10 domains) plus a small
synthetic sample episode, so it works out of the box; upload your own Episode to analyse it. Code:
[`tarski_dre/`](tarski_dre/); API: [`forensic_app/dre_api.py`](forensic_app/dre_api.py). Best quality
with `mistral-small`.

## Layout
- `forensic_app/` — FastAPI app, static UI, launchers, updater, desktop packaging
- `local_engine/` — the analysis engine + non-confidential sample decks
- `tarski_dre/` — the Learning DRE (deterministic core + reasoning layer) + bundled sample episode

Decision-support, not financial/legal advice.
