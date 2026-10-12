@echo off
cd /d C:\git-repo\pet
set "PYTHONPATH="
set "CUA_FIND_INVALID_PYTHON="
start "" /B ".venv\Scripts\python.exe" -u tools\_m2_watch.py tools\_m2work 1 7200 > tools\_m2_watch.log 2>&1
