"""Windows specifics: where Ollama lives, silent per-user install, parent-process check."""
import os
import subprocess
import tempfile

NAME = "windows"

OLLAMA_SETUP_URL = "https://ollama.com/download/OllamaSetup.exe"


def ollama_candidates():
    la = os.environ.get("LOCALAPPDATA", "")
    return [os.path.join(la, "Programs", "Ollama", "ollama.exe")] if la else []


def install_ollama(ctx):
    """Download the official installer and run it silently (per-user, no admin)."""
    dst = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
    ctx.log("  downloading Ollama installer...")
    ctx.download(OLLAMA_SETUP_URL, dst, "Downloading the local AI runtime (Ollama)")
    # We don't know if Ollama's installer is Inno or NSIS, so try both silent conventions,
    # then fall back to a normal (click-through) run. Stop as soon as ollama appears.
    for flags in (["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], ["/S"], []):
        try:
            subprocess.run([dst] + flags, timeout=600)
        except Exception:
            continue
        if ctx.ollama_found() or ctx.ollama_up():
            return True
    return ctx.ollama_found() or ctx.ollama_up()


def parent_alive(pid):
    # os.kill(pid, 0) would TERMINATE the process on Windows — query it via the Win32 API instead.
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        code = ctypes.c_ulong()
        k32.GetExitCodeProcess(h, ctypes.byref(code))
        return code.value == 259                     # STILL_ACTIVE
    finally:
        k32.CloseHandle(h)
