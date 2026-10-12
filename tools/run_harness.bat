@echo off
cd /d "%~dp0\.."
set "PYTHONPATH=%~dp0\.."
start "" ".venv\Scripts\python.exe" "tools\harness_flow.py"
