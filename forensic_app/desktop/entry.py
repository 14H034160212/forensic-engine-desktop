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
import os, sys, time, threading, webbrowser, urllib.request, shutil, subprocess, traceback, datetime

PORT = int(os.environ.get("PORT", "8808"))
os.environ.setdefault("MODELS", "llama3.2:3b,qwen2.5-coder:7b")

# When launched by the Tauri window (NO_BROWSER=1) we must NOT also pop a system browser.
NO_BROWSER = os.environ.get("NO_BROWSER", "").strip() in ("1", "true", "yes")

# On Windows the app runs with no console, so stdout is lost — mirror key events to a log file
# the user can send us if startup fails.
LOG_PATH = os.path.join(os.path.expanduser("~"), ".forensic_engine", "engine.log")
def log(msg):
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line, flush=True)
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

def _ensure_ollama():
    """If Ollama is installed but not running, start it. If not installed, tell the user."""
    if _ollama_up():
        return True
    exe = shutil.which("ollama")
    if exe:
        try:
            subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(10):
                time.sleep(1)
                if _ollama_up():
                    print("  ✓ started Ollama"); return True
        except Exception:
            pass
    return False

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

def main():
    log(f"Forensic Engine starting (port {PORT}, frozen={getattr(sys,'frozen',False)})")
    try:
        if not _ensure_ollama():
            log("  ! Ollama not detected on 127.0.0.1:11434 — install from https://ollama.com/download")
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
