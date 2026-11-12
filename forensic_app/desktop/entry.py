#!/usr/bin/env python3
"""
Native-app entrypoint for the Forensic Engine (PyInstaller / Tauri sidecar).

Bundled into a single executable so the end user needs NO Python install. On launch it:
  1. picks a laptop-friendly default model,
  2. checks the local Ollama is reachable (warns, doesn't hard-fail),
  3. starts the FastAPI app on a local port,
  4. opens the default browser at it.

Note: Ollama itself is a separate native install (https://ollama.com) — a packaged app cannot
bundle it. If Ollama isn't running, the UI still loads and shows the problem on first analysis.
"""
import os, sys, time, threading, webbrowser, urllib.request, shutil, subprocess, traceback, datetime, socket

import platforms          # per-OS behaviour: platforms/mac.py, platforms/windows.py, platforms/linux.py

# Force UTF-8 everywhere — on a Chinese/Japanese Windows the default codec is GBK/CP932, which
# crashes when writing findings that contain characters like '‑' (non-breaking hyphen).
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

DATA_DIR = os.path.join(os.path.expanduser("~"), ".forensic_engine")

def _pick_port():
    """Honour an explicit PORT; otherwise grab a FREE OS-assigned port so we never collide with
    whatever else is on the machine (VS Code, other dev servers, a leftover instance...)."""
    env = os.environ.get("PORT")
    if env:
        return int(env)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p

PORT = _pick_port()
PORT_FILE = os.path.join(DATA_DIR, "port")     # the Tauri shell reads this to find the window URL
# Model menu (first = default). The DEFAULT is the small model we auto-provision on first run so the
# app works with ZERO manual setup; gemma4:26b is offered as the high-accuracy opt-in (big download +
# ~16GB RAM). Keeping the small ones for weak machines.
DEFAULT_MODEL = "qwen2.5-coder:7b"
os.environ.setdefault("MODELS", "qwen2.5-coder:7b,gemma4:26b,gpt-oss:20b,llama3.2:3b")
# Turn the routed domain rulebook ON by default — it is what delivers the recall (blind engine alone
# is ~15%). Router-gated + precision-guarded.
os.environ.setdefault("USE_PACKS", "1")

SETUP_FILE = os.path.join(DATA_DIR, "setup.json")   # first-run auto-setup progress (frontend polls it)

# When launched by the Tauri window (NO_BROWSER=1) we must NOT also pop a system browser.
NO_BROWSER = os.environ.get("NO_BROWSER", "").strip() in ("1", "true", "yes")

# On Windows the app runs with no console, so stdout is lost — mirror key events to a log file
# the user can send us if startup fails.
LOG_PATH = os.path.join(DATA_DIR, "engine.log")
def log(msg):
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')}  {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass        # stdout is a pipe to the Tauri shell; once the shell exits it's broken (BrokenPipeError)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def _ollama_up():
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False

import json as _json
def _write_setup(stage, percent=None, message="", done=False, error=""):
    """Publish first-run setup progress; the frontend polls /api/setup and shows a progress banner."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETUP_FILE, "w", encoding="utf-8") as f:
            _json.dump({"stage": stage, "percent": percent, "message": message,
                        "done": done, "error": error, "model": DEFAULT_MODEL,
                        "ts": datetime.datetime.now().isoformat(timespec="seconds")}, f)
    except Exception:
        pass

class _PlatformCtx:
    """Helpers handed to platforms.<os>.install_ollama() so platform code never imports entry.py."""
    log = staticmethod(log)
    ollama_up = staticmethod(lambda: _ollama_up())
    ollama_found = staticmethod(lambda: _ollama_binary() is not None)
    @staticmethod
    def download(url, dst, label):
        """urlretrieve with % published to the setup file, so a ~200MB download isn't a silent wait."""
        def hook(blocks, bsize, total):
            if total and total > 0:
                pct = min(100, int(blocks * bsize * 100 / total))
                _write_setup("install-ollama", pct, f"{label}... {pct}%")
        urllib.request.urlretrieve(url, dst, reporthook=hook)

def _ollama_binary():
    """Find an ollama executable: PATH, a bundled sidecar next to us, or the OS's standard install
    locations (see platforms/<os>.py)."""
    exe = shutil.which("ollama")
    if exe: return exe
    here = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__)
    cands = [os.path.join(here, "ollama.exe"), os.path.join(here, "ollama")]
    cands += platforms.ollama_candidates()
    for c in cands:
        if c and os.path.exists(c): return c
    return None

def _install_ollama():
    """Auto-install Ollama with no manual step — how is per-OS, in platforms/<os>.py.
    If it fails, the UI guides the user to the download page."""
    _write_setup("install-ollama", None, "Installing the local AI runtime (Ollama)...")
    try:
        return bool(platforms.install_ollama(_PlatformCtx))
    except Exception:
        log("  ! auto-install Ollama failed:\n" + traceback.format_exc())
    return False

def _ensure_ollama():
    """Ensure Ollama is RUNNING — start it if installed, auto-install it if not, all with no manual step."""
    if _ollama_up():
        return True
    exe = _ollama_binary()
    if not exe:
        if not _install_ollama():
            return False
        exe = _ollama_binary()
    try:
        if exe:
            subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    for _ in range(30):
        time.sleep(1)
        if _ollama_up():
            log("  ✓ Ollama running"); return True
    return False

def _has_model(name):
    try:
        import json as J
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=4) as r:
            have = [m.get("name", "") for m in J.load(r).get("models", [])]
        return name in have
    except Exception:
        return False

def _pull_model(name):
    """Pull the default model via Ollama's streaming /api/pull, reporting % to the setup file so the
    user sees progress instead of a mystery wait. No manual `ollama pull` needed."""
    _write_setup("pull-model", 0, f"Downloading the default model ({name})...")
    try:
        import json as J
        req = urllib.request.Request("http://127.0.0.1:11434/api/pull",
                                     data=J.dumps({"model": name}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3600) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line: continue
                try: d = J.loads(line)
                except Exception: continue
                tot, comp = d.get("total"), d.get("completed")
                pct = int(comp * 100 / tot) if tot and comp else None
                _write_setup("pull-model", pct, d.get("status", "") + (f" {pct}%" if pct is not None else ""))
                if d.get("error"):
                    _write_setup("pull-model", None, "", error=d["error"]); return False
        return _has_model(name)
    except Exception:
        log("  ! model pull failed:\n" + traceback.format_exc())
        _write_setup("pull-model", None, "", error="model download failed"); return False

def _autosetup():
    """Background first-run provisioning: Ollama up (install if needed) → default model present (pull
    if needed). Everything automatic, progress surfaced via /api/setup. Idempotent + safe to no-op."""
    try:
        if not _ensure_ollama():
            _write_setup("need-ollama", None, "", error="Ollama could not be installed automatically")
            return
        if not _has_model(DEFAULT_MODEL):
            if not _pull_model(DEFAULT_MODEL):
                return
        _write_setup("ready", 100, "Ready.", done=True)
    except Exception:
        log("  ! autosetup crashed:\n" + traceback.format_exc())

def _open_browser():
    if NO_BROWSER:
        return
    url = f"http://127.0.0.1:{PORT}/"
    for _ in range(40):                      # wait until the server answers, then open once
        try:
            urllib.request.urlopen(url, timeout=1); break
        except Exception:
            time.sleep(0.5)
    webbrowser.open(url)

def _watch_parent():
    """Exit when the Tauri shell that launched us is gone. Without this, quitting the app (or the
    shell crashing / being force-quit) leaves this Python server running in the background forever —
    a PyInstaller onefile child is reparented to launchd/init, so it never sees the window close."""
    try:
        ppid = int(os.environ.get("FE_PARENT_PID", "0"))
    except ValueError:
        ppid = 0
    if ppid <= 0:
        return                                   # not launched by the shell (dev run / CLI) → no-op
    def loop():
        try:
            while platforms.parent_alive(ppid):
                time.sleep(2)
            log("  shell exited -> shutting down engine")
        finally:
            os._exit(0)          # never let a logging error keep the orphan alive
    threading.Thread(target=loop, daemon=True).start()

def main():
    log(f"Forensic Engine starting (port {PORT}, frozen={getattr(sys,'frozen',False)})")
    _watch_parent()
    try:
        # First-run auto-setup (install Ollama if missing, pull the default model) runs in the BACKGROUND
        # so the window opens instantly and shows a progress banner instead of blocking on a GB download.
        _write_setup("starting", None, "Starting...")
        threading.Thread(target=_autosetup, daemon=True).start()
        # publish the chosen port so the Tauri shell knows where to point the window
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(PORT_FILE, "w", encoding="utf-8") as f:
                f.write(str(PORT))
        except Exception:
            log("  ! could not write port file: " + traceback.format_exc())
        import uvicorn
        from server import app
        threading.Thread(target=_open_browser, daemon=True).start()
        log(f"  serving on http://127.0.0.1:{PORT}/")
        uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
    except Exception:
        log("FATAL: engine failed to start:\n" + traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
