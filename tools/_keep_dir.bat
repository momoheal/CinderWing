@echo off
rem 开发期间守护 harness 临时目录（自动适应轮换的 lr_* 目录）。
rem 双击运行，最小化即可；会话结束后关掉本黑窗口。
cd /d C:\git-repo\pet
set "PYTHONPATH="
set "CUA_FIND_INVALID_PYTHON="
:loop
".venv\Scripts\python.exe" tools\_keep_dirs.py
timeout /t 2 /nobreak >nul
goto loop
