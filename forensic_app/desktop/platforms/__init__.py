"""
Per-OS behaviour for the desktop app, kept out of entry.py so each platform reads on its own.

Every platform module exposes the same three functions:

    ollama_candidates()      -> list of paths where an installed `ollama` binary may live
    install_ollama(ctx)      -> bool   auto-install Ollama with no manual step
    parent_alive(pid)        -> bool   is the Tauri shell process still running?

`ctx` is a small helper object from entry.py (logging, progress-reporting download, a re-check
for the binary) so platform code never imports entry.py back.

    mac.py      — macOS (Apple Silicon / Intel)
    windows.py  — Windows 10/11
    linux.py    — Linux (no auto-install; the UI links to ollama.com)

The explicit imports below (not importlib) let PyInstaller see every module.
"""
import sys

if sys.platform == "darwin":
    from . import mac as current
elif sys.platform.startswith("win"):
    from . import windows as current
else:
    from . import linux as current

NAME = current.NAME
ollama_candidates = current.ollama_candidates
install_ollama = current.install_ollama
parent_alive = current.parent_alive
