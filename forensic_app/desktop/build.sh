#!/usr/bin/env bash
# Build the Forensic Engine into a single native executable (macOS / Linux).
# Requires: pip install pyinstaller  (in an env that also has the app's runtime deps).
# NOTE: PyInstaller cannot cross-compile — run this ON the OS you want a binary for.
# The heavy ML verifier (torch/transformers/logic_verifier) is EXCLUDED on purpose: the
# native client is the light tier; contradiction verification degrades gracefully without it.
set -e
R="$(cd "$(dirname "$0")/../.." && pwd)"          # project root
SEP=":"                                            # PyInstaller --add-data separator
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) SEP=";";; esac   # Windows (git-bash) needs ';'
PY=python3; command -v python3 >/dev/null 2>&1 || PY=python
cd "$R"
"$PY" -m PyInstaller --onefile --name ForensicEngine \
  --distpath "$R/desktop_dist" --workpath /tmp/pyi_work --specpath /tmp/pyi_spec \
  --paths "$R/forensic_app" --paths "$R/local_engine" \
  --add-data "$R/forensic_app/static${SEP}forensic_app/static" \
  --add-data "$R/forensic_app/VERSION${SEP}forensic_app" \
  --add-data "$R/local_engine/decks${SEP}local_engine/decks" \
  --hidden-import pdfplumber --hidden-import pypdf --hidden-import docx --hidden-import multipart \
  --collect-all pdfminer --collect-submodules uvicorn \
  --exclude-module torch --exclude-module transformers --exclude-module peft \
  --exclude-module amrlib --exclude-module sentencepiece --exclude-module datasets \
  --exclude-module logic_verifier --exclude-module amr_transforms --exclude-module amr_lda_funcs \
  --exclude-module scipy --exclude-module sklearn --exclude-module matplotlib --exclude-module pandas \
  "$R/forensic_app/desktop/entry.py"
echo "✓ built: $R/desktop_dist/ForensicEngine"
