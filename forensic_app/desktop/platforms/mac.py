"""macOS specifics: where Ollama lives, how to install it without admin, parent-process check."""
import os
import shutil
import subprocess
import tempfile

NAME = "macos"

# Per-user Applications folder: installing here needs no admin password.
USER_APPS = os.path.join(os.path.expanduser("~"), "Applications")
OLLAMA_ZIP_URL = "https://ollama.com/download/Ollama-darwin.zip"


def ollama_candidates():
    # An app launched from Finder/Dock gets a minimal PATH (/usr/bin:/bin:...), so `which` misses
    # Homebrew and the CLI symlink — list the standard macOS locations explicitly.
    return [os.path.join(d, "Ollama.app", "Contents", "Resources", "ollama")
            for d in (USER_APPS, "/Applications")] + [
        "/usr/local/bin/ollama",        # CLI symlink from Ollama.app / Intel Homebrew
        "/opt/homebrew/bin/ollama",     # Apple Silicon Homebrew
    ]


def install_ollama(ctx):
    """Download the official Ollama.app and unpack it into ~/Applications (no admin, no installer
    UI). entry.py then runs its bundled CLI headless (`ollama serve`), so Ollama's own first-run
    wizard — which asks for an admin password to symlink the CLI — never appears."""
    tmp = tempfile.mkdtemp(prefix="ollama_dl_")
    try:
        zp = os.path.join(tmp, "Ollama-darwin.zip")
        ctx.log("  downloading Ollama for macOS...")
        ctx.download(OLLAMA_ZIP_URL, zp, "Downloading the local AI runtime (Ollama)")
        os.makedirs(USER_APPS, exist_ok=True)
        # ditto (not zipfile) keeps the app's symlinks, permissions and code signature intact.
        subprocess.run(["/usr/bin/ditto", "-x", "-k", zp, USER_APPS], check=True, timeout=600)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ok = ctx.ollama_found()
    ctx.log("  ✓ Ollama unpacked to ~/Applications" if ok else "  ! Ollama.app not found after unpack")
    return ok


def parent_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True     # exists, owned by someone else
