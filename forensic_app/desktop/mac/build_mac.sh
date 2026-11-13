#!/usr/bin/env bash
# One-shot local build of the macOS app: engine (PyInstaller) -> Tauri sidecar -> .app + .dmg.
#
# Prerequisites (once):
#   - Xcode Command Line Tools          xcode-select --install
#   - Rust + Tauri CLI                  https://rustup.rs   then   cargo install tauri-cli --version "^2" --locked
#   - Python 3.11 with the app deps     pip install -r forensic_app/requirements-laptop.txt pyinstaller
#     (or set PYTHON=/path/to/venv/bin/python)
#
# Output: desktop_dist/mac/ForensicEngine-mac-<arch>.dmg   (same file name CI publishes)
set -euo pipefail
[ "$(uname -s)" = "Darwin" ] || { echo "build_mac.sh must run on macOS"; exit 1; }

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TAURI="$ROOT/forensic_app/desktop/tauri"
PYTHON="${PYTHON:-python3}"
VERSION="$(tr -d '[:space:]' < "$ROOT/forensic_app/VERSION")"
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

command -v cargo >/dev/null || { echo "✗ Rust not found — install from https://rustup.rs"; exit 1; }
cargo tauri --version >/dev/null 2>&1 || { echo "✗ Tauri CLI not found — cargo install tauri-cli --version '^2' --locked"; exit 1; }
"$PYTHON" -m PyInstaller --version >/dev/null 2>&1 || { echo "✗ PyInstaller not found for $PYTHON"; exit 1; }

TRIPLE="$(rustc -vV | sed -n 's/host: //p')"          # aarch64-apple-darwin or x86_64-apple-darwin
case "$TRIPLE" in aarch64-*) ARCH=arm64;; x86_64-*) ARCH=x64;; *) ARCH="$TRIPLE";; esac
echo "▸ Forensic Engine $VERSION for macOS ($ARCH)"

echo "▸ [1/4] engine (PyInstaller)"
PATH="$(dirname "$PYTHON"):$PATH" bash "$ROOT/forensic_app/desktop/build.sh" >/tmp/fe_pyinstaller.log 2>&1 \
  || { tail -30 /tmp/fe_pyinstaller.log; echo "✗ PyInstaller failed (full log: /tmp/fe_pyinstaller.log)"; exit 1; }

# A python.org / setup-python CPython ships stdlib C extensions as separate lib-dynload/*.so files;
# the onefile engine would unpack + security-check ~55 of them on every launch (~10 s slower start).
"$PYTHON" -I -c "
from PyInstaller.archive.readers import CArchiveReader
n = sum('lib-dynload/' in x for x in CArchiveReader('$ROOT/desktop_dist/ForensicEngine').toc)
assert n == 0, f'{n} lib-dynload .so files bundled: use uv\'s standalone CPython (see mac/README.md)'
" || exit 1

echo "▸ [2/4] sidecar"
mkdir -p "$TAURI/src-tauri/binaries"
install -m 755 "$ROOT/desktop_dist/ForensicEngine" "$TAURI/src-tauri/binaries/engine-server-$TRIPLE"

echo "▸ [3/4] icons"
( cd "$TAURI" && cargo tauri icon src-tauri/icon-source.png >/dev/null )

echo "▸ [4/4] app + dmg (Tauri)"
# version + mac-only bundle targets are passed as overrides, so tauri.conf.json stays untouched
( cd "$TAURI" && cargo tauri build --target "$TRIPLE" --bundles app,dmg \
    --config "{\"version\":\"$VERSION\"}" )

OUT="$ROOT/desktop_dist/mac"; mkdir -p "$OUT"
BUNDLE="$TAURI/src-tauri/target/$TRIPLE/release/bundle"
DMG="$(ls -t "$BUNDLE"/dmg/*.dmg | head -1)"          # newest (older versions may linger in target/)
cp "$DMG" "$OUT/ForensicEngine-mac-$ARCH.dmg"
codesign --verify --deep --strict "$BUNDLE/macos/Forensic Engine.app" && echo "✓ signature valid (ad-hoc)"
echo "✓ $OUT/ForensicEngine-mac-$ARCH.dmg"
