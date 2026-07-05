# Native desktop build (zero-Python client)

Package the Forensic Engine into a **single native executable** so an end user runs it with
**no Python install** — double-click, it starts the local server and opens the browser.

## What this is / isn't
- ✅ No Python needed on the user's machine — the interpreter + app are inside the binary.
- ✅ Cross-OS *approach* (PyInstaller works on macOS / Windows / Linux).
- ⚠️ **Ollama is still a separate install** (https://ollama.com). A packaged app can't bundle
  Ollama's multi-GB service. On launch the app checks for it and warns if missing; the UI still
  opens. This is "zero-Python", not "zero-install".
- ⚠️ **PyInstaller cannot cross-compile** — build a Windows `.exe` on Windows, a macOS app on
  macOS, a Linux binary on Linux (or use CI, e.g. GitHub Actions with a matrix of OS runners).
- ⚠️ The heavy ML **verifier is excluded** (torch/transformers). The native client is the light
  tier: contradiction verification degrades gracefully (raw bonds shown). That keeps the binary
  ~100 MB instead of multi-GB.

## Build
```bash
pip install pyinstaller          # in an env that also has the app's runtime deps
# macOS / Linux:
./build.sh
# Windows:
build.bat
```
Output: `desktop_dist/ForensicEngine` (`.exe` on Windows). Verified on Linux: 105 MB single file,
boots in ~6 s, serves the full app on http://127.0.0.1:8808/ (samples/version/engine all resolve
from the frozen bundle).

## Run
Double-click the binary (or run it). It starts the app on 127.0.0.1:8808 and opens your browser.
Writable data (run history) goes to `~/.forensic_engine/`. Set `PORT` / `MODELS` env vars to
override.

## Next step — Tauri (optional polish)
PyInstaller gives a real binary but the UI is a browser tab. For a proper app **window + icon +
installer**, wrap this binary as a **Tauri sidecar**: Tauri (Rust, ~3 MB shell) opens a native
webview pointed at the sidecar's 127.0.0.1 port. That yields a `.dmg` / `.msi` / `.AppImage`
installer. Tauri also can't cross-compile — same per-OS build story.
