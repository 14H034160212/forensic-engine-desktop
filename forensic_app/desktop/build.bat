@echo off
rem Build the Forensic Engine into a single native .exe (Windows).
rem Requires: pip install pyinstaller  (in an env that also has the app's runtime deps).
rem PyInstaller cannot cross-compile — run this ON Windows to get a Windows .exe.
rem The heavy ML verifier (torch/transformers) is EXCLUDED: the native client is the light tier.
setlocal
set R=%~dp0..\..
pushd "%R%"
python -m PyInstaller --onefile --name ForensicEngine ^
  --distpath "%R%\desktop_dist" --workpath "%TEMP%\pyi_work" --specpath "%TEMP%\pyi_spec" ^
  --paths "%R%\forensic_app" --paths "%R%\local_engine" ^
  --add-data "%R%\forensic_app\static;forensic_app/static" ^
  --add-data "%R%\forensic_app\VERSION;forensic_app" ^
  --add-data "%R%\local_engine\decks;local_engine/decks" ^
  --hidden-import pdfplumber --hidden-import pypdf --hidden-import docx --hidden-import multipart ^
  --collect-all pdfminer --collect-submodules uvicorn ^
  --exclude-module torch --exclude-module transformers --exclude-module peft ^
  --exclude-module amrlib --exclude-module sentencepiece --exclude-module datasets ^
  --exclude-module logic_verifier --exclude-module amr_transforms --exclude-module amr_lda_funcs ^
  --exclude-module scipy --exclude-module sklearn --exclude-module matplotlib --exclude-module pandas ^
  "%R%\forensic_app\desktop\entry.py"
popd
echo Done: %R%\desktop_dist\ForensicEngine.exe
