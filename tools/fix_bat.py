# One-off fixer: rewrite 启动宠物.bat as ASCII with CRLF line endings (cmd.exe requirement).
lines = [
    "@echo off",
    'cd /d "%~dp0"',
    r'".venv\Scripts\python.exe" -m app.main',
    "if errorlevel 1 pause",
]
target = r"C:\git-repo\pet\启动宠物.bat"
with open(target, "wb") as f:
    f.write(("\r\n".join(lines) + "\r\n").encode("ascii"))
print(open(target, "rb").read().decode())
