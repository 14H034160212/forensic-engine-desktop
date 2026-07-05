# Tauri packaging (native window + installers)

Wraps the PyInstaller binary (see `../`) as a **Tauri sidecar** so you get a real desktop app —
native window, app icon, and platform installers (`.dmg` / `.msi` / `.AppImage`). Everything
runs on 127.0.0.1; nothing leaves the machine.

> **Status: scaffold, not yet built.** The build box here has no Rust toolchain and Tauri can't
> cross-compile. These files are a correct-as-authored starting point — expect to iterate when
> you build on a real dev machine per below.

## Prerequisites (on the target OS)
- Rust + Cargo — https://rustup.rs
- Tauri CLI — `cargo install tauri-cli --version "^2"`
- Node not required (we ship no JS frontend — the UI is served by the sidecar).
- The platform's Tauri deps (WebView2 on Windows, webkit2gtk on Linux, Xcode CLT on macOS).

## Wire up the sidecar (per OS)
1. Build the PyInstaller binary first: `../build.sh` (or `../build.bat`) → `desktop_dist/ForensicEngine`.
2. Copy it into Tauri's sidecar slot with the Rust **target triple** suffix, e.g.:
   - macOS arm64:  `src-tauri/binaries/forensic-engine-aarch64-apple-darwin`
   - Windows x64:  `src-tauri/binaries/forensic-engine-x86_64-pc-windows-msvc.exe`
   - Linux x64:    `src-tauri/binaries/forensic-engine-x86_64-unknown-linux-gnu`
   (Find yours with `rustc -Vv | grep host`.)
3. Add real icons to `src-tauri/icons/` (`cargo tauri icon path/to/logo.png` generates all sizes).

## Build the installer
```bash
cd src-tauri
cargo tauri build
```
Output: `src-tauri/target/release/bundle/{dmg,msi,nsis,appimage}/…`.

## Notes / gotchas to expect
- **CSP**: `tauri.conf.json` sets `security.csp = null` so the window can navigate to the
  localhost server. Tighten later if desired.
- **Race**: `main.rs` waits (TCP connect to :8808) before loading the URL — first launch also
  waits on Ollama model pull, so allow generous time.
- **Ollama** is still a separate install (same as the PyInstaller build) — the app detects it and
  shows the onboarding banner.
- **CI**: extend `.github/workflows/build-desktop.yml` with a Rust setup + `cargo tauri build`
  step to produce installers per OS automatically.
