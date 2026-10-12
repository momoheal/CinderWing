@echo off
cd /d "%~dp0"
set "PYTHONPATH="
set "CUA_FIND_INVALID_PYTHON="
start "" ".venv\Scripts\pythonw.exe" -m app.main
