# Windows build

## For users
Download `ForensicEngine-windows-x64-setup.exe` from the
[latest release](https://github.com/14H034160212/forensic-engine-desktop/releases/latest) and run it
(per-user install, no admin). If SmartScreen warns: **More info → Run anyway**.

- **Ollama** is installed automatically (silent per-user installer) and the default model (~4.7 GB) is
  downloaded on first launch.
- Logs: `%USERPROFILE%\.forensic_engine\engine.log`.

## Build
Installers are built by CI on a Windows runner ([`build-installers.yml`](../../../.github/workflows/build-installers.yml)) —
push a `v*` tag or run the workflow manually. To build only the engine binary locally on Windows:
```bat
pip install -r forensic_app\requirements-laptop.txt pyinstaller
forensic_app\desktop\build.bat
```
Then follow [`../tauri/README.md`](../tauri/README.md) to wrap it into an installer.

## Windows-specific code
| What | Where |
|---|---|
| Find / auto-install Ollama, parent-process check (Win32 API — `os.kill(pid, 0)` would kill the process on Windows) | [`../platforms/windows.py`](../platforms/windows.py) |
| UTF-8 stdio (GBK/CP932 locales) | top of [`../entry.py`](../entry.py) |
| Engine build script | [`../build.bat`](../build.bat) |
