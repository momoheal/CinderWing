"""Rewrite 启动宠物.bat as pure ASCII + CRLF, launching pythonw detached."""
import os

bat = (
    "@echo off\r\n"
    'cd /d "%~dp0"\r\n'
    'set "PYTHONPATH="\r\n'
    'set "CUA_FIND_INVALID_PYTHON="\r\n'
    'start "" ".venv\\Scripts\\pythonw.exe" -m app.main\r\n'
)
path = r"C:\git-repo\pet\启动宠物.bat"
with open(path, "wb") as f:
    f.write(bat.encode("ascii"))
print("written", path)
