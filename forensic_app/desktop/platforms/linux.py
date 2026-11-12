"""Linux specifics. No auto-install (Ollama's Linux installer needs root); the UI links to ollama.com."""
import os

NAME = "linux"


def ollama_candidates():
    return ["/usr/local/bin/ollama", "/usr/bin/ollama"]


def install_ollama(ctx):
    ctx.log("  Ollama not found; auto-install is not supported on Linux (see https://ollama.com/download)")
    return False


def parent_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
