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

## Layout
- `forensic_app/` — FastAPI app, static UI, launchers, updater, desktop packaging
- `local_engine/` — the analysis engine + non-confidential sample decks

Decision-support, not financial/legal advice.
