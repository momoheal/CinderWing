"""Write a detached launcher bat for the flow harness (ASCII + CRLF)."""
bat = (
    "@echo off\r\n"
    'cd /d "%~dp0\\.."\r\n'
    'set "PYTHONPATH=%~dp0\\.."\r\n'
    'start "" ".venv\\Scripts\\python.exe" "tools\\harness_flow.py"\r\n'
)
with open(r"C:\git-repo\pet\tools\run_harness.bat", "wb") as f:
    f.write(bat.encode("ascii"))
print("ok")
