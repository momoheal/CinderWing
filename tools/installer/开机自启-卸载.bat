@echo off
rem Remove the auto-start shortcut (the program itself is kept).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall_autostart.ps1"
pause
