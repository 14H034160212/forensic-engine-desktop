@echo off
rem Forensic Engine - LAPTOP EDITION (Windows) / 取证引擎 - 笔记本版 (Windows)
rem Runs the whole product locally on a small model. Nothing leaves the laptop.
rem 整套产品在本机用小模型运行,数据不出这台笔记本。
rem One-time: install Ollama (https://ollama.com) and Python 3.9+ with the deps in
rem requirements-laptop.txt.  Then just double-click this file, or run: laptop.bat
rem 首次:装 Ollama 和 Python 3.9+,pip install -r requirements-laptop.txt,然后双击本文件。
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
if "%PORT%"=="" set PORT=8800

rem ---- 1) pick a model tier for THIS machine / 为本机挑选模型档位 ----
set RAM_GB=8
for /f %%A in ('powershell -NoProfile -Command "[math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)" 2^>nul') do set RAM_GB=%%A
set HAS_GPU=0
where nvidia-smi >nul 2>&1 && set HAS_GPU=1

if not "%FORCE_MODELS%"=="" (
  set MODELS_ENV=%FORCE_MODELS%
) else if !RAM_GB! GEQ 16 (
  set MODELS_ENV=qwen2.5-coder:7b,llama3.2:3b
) else if "!HAS_GPU!"=="1" (
  set MODELS_ENV=qwen2.5-coder:7b,llama3.2:3b
) else (
  set MODELS_ENV=llama3.2:3b
)
for /f "tokens=1 delims=," %%M in ("!MODELS_ENV!") do set DEF=%%M
echo [*] Detected !RAM_GB!GB RAM, GPU=!HAS_GPU!  -^>  default model: !DEF!
echo     检测到 !RAM_GB!GB 内存, GPU=!HAS_GPU!  -^>  默认模型: !DEF!

rem ---- 2) make sure Ollama is up / 确保 Ollama 已启动 ----
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
  echo [*] starting Ollama... / 启动 Ollama...
  start "" /b ollama serve
  timeout /t 4 >nul
)

rem ---- 3) pull the model(s) / 拉取模型(首次下载 2-4.5GB,之后缓存) ----
for %%M in (!MODELS_ENV:,= !) do (
  echo [*] ensuring model %%M ... / 准备模型 %%M...
  ollama pull %%M
)

rem ---- 4) run the app locally and open the browser / 本地启动并打开浏览器 ----
set MODELS=!MODELS_ENV!
echo [*] Forensic Engine (laptop) -^> http://127.0.0.1:!PORT!/   (nothing leaves this machine / 数据不出本机)
start "" /b cmd /c "timeout /t 3 >nul & start "" http://127.0.0.1:!PORT!/"
python -m uvicorn server:app --host 127.0.0.1 --port !PORT!
