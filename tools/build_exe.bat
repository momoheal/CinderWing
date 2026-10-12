@echo off
rem Build the desktop pet into dist\ and seed installer scripts. ASCII-only.
cd /d "%~dp0\.."
set "PYTHONPATH="
set "CUA_FIND_INVALID_PYTHON="
".venv\Scripts\python.exe" -m PyInstaller --clean -y --noconfirm pet.spec
".venv\Scripts\python.exe" tools\post_build.py
echo BUILD_DONE
