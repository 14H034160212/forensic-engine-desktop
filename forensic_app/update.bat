@echo off
rem Forensic Engine - one-click updater (Windows). / 一键更新 (Windows)
rem Pulls the latest build and overwrites code, KEEPING your runs/ history and uploads/.
rem 拉取最新版覆盖代码,保留 runs/ 历史与 uploads/。Cached Ollama models untouched.
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
set ROOT=%~dp0..
if "%UPDATE_SOURCE%"=="" set UPDATE_SOURCE=https://forensic-engine.example
set URL=%UPDATE_SOURCE%/local_deploy.zip

set OLD=unknown
if exist VERSION set /p OLD=<VERSION
echo [*] current version: !OLD!
echo [*] downloading latest from !URL! ...

set TMP=%TEMP%\fe_update_%RANDOM%
mkdir "%TMP%" 2>nul
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '!URL!' -Headers @{'ngrok-skip-browser-warning'='1'} -OutFile '%TMP%\u.zip'; Expand-Archive -Force '%TMP%\u.zip' '%TMP%\x' } catch { exit 1 }"
if errorlevel 1 ( echo [x] download/extract failed / 下载或解压失败 & rmdir /s /q "%TMP%" 2>nul & exit /b 1 )
set SRC=%TMP%\x\local_deploy
if not exist "%SRC%\forensic_app" ( echo [x] bad bundle / 包无效 & rmdir /s /q "%TMP%" 2>nul & exit /b 1 )

rem overwrite code; runs/ + uploads/ are not in the bundle so your data stays
xcopy /E /Y /I /Q "%SRC%\forensic_app" "%ROOT%\forensic_app" >nul
xcopy /E /Y /I /Q "%SRC%\local_engine" "%ROOT%\local_engine" >nul
if exist "%SRC%\CLAUDE.md" copy /Y "%SRC%\CLAUDE.md" "%ROOT%\CLAUDE.md" >nul
if exist "%SRC%\START-HERE.md" copy /Y "%SRC%\START-HERE.md" "%ROOT%\START-HERE.md" >nul
rmdir /s /q "%TMP%" 2>nul

set NEW=unknown
if exist VERSION set /p NEW=<VERSION
echo [*] updated: !OLD!  -^>  !NEW!
echo [*] restart to apply:  laptop.bat   (models cached; fast startup)
