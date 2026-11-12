# macOS build

## For users
Download `ForensicEngine-mac-arm64.dmg` from the
[latest release](https://github.com/14H034160212/forensic-engine-desktop/releases/latest), open it, and drag
**Forensic Engine** into **Applications**.

- **First launch**: the app isn't notarized yet, so macOS says it can't verify the developer.
  Open **System Settings → Privacy & Security** and click **Open Anyway** (once).
- **Ollama** is installed automatically into `~/Applications/Ollama.app` (no admin password) and the default
  model (~4.7 GB) is downloaded on first launch. An existing Ollama in `/Applications` or Homebrew is reused.
- Logs: `~/.forensic_engine/engine.log`.
- Uninstall: delete the app; optionally `~/.forensic_engine`, `~/Applications/Ollama.app` and `~/.ollama`.

## Build locally
Prerequisites (once):
```bash
xcode-select --install                                   # Command Line Tools
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
cargo install tauri-cli --version "^2" --locked
uv venv -p 3.11 .venv311 && uv pip install -p .venv311 -r forensic_app/requirements-laptop.txt pyinstaller
```
Build (from the repo root):
```bash
PYTHON=.venv311/bin/python forensic_app/desktop/mac/build_mac.sh
```
Output: `desktop_dist/mac/ForensicEngine-mac-arm64.dmg` (same name CI publishes).

## macOS-specific code
| What | Where |
|---|---|
| Find / auto-install Ollama, parent-process check | [`../platforms/mac.py`](../platforms/mac.py) |
| Code-signing entitlements (PyInstaller engine needs `disable-library-validation` under the hardened runtime) | [`../tauri/src-tauri/Entitlements.plist`](../tauri/src-tauri/Entitlements.plist) |
| Ad-hoc signing (`signingIdentity: "-"`) | `bundle.macOS` in [`../tauri/src-tauri/tauri.conf.json`](../tauri/src-tauri/tauri.conf.json) |

## Signing & notarization (not done yet)
Without an Apple Developer ID the app is ad-hoc signed: it opens after one **Open Anyway**. To make it open
with no warning at all, enrol in the Apple Developer Program, then add these GitHub secrets and Tauri will
sign + notarize in CI: `APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGNING_IDENTITY`,
`APPLE_ID`, `APPLE_PASSWORD` (app-specific), `APPLE_TEAM_ID` — and set `signingIdentity` to the Developer ID.
