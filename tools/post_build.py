"""打包后处理：把开机自启脚本和使用说明复制进 dist 成品文件夹，
并统一编码（ps1/txt 用 UTF-8 BOM，bat 用 ASCII + CRLF）。"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "installer"
DST = ROOT / "dist" / "CinderWing"

assert DST.exists(), f"dist folder not found: {DST}"

for f in SRC.iterdir():
    if not f.is_file():
        continue
    # utf-8-sig：源文件无论是否带 BOM 都先剥掉，输出时统一只加一个 BOM，
    # 否则双重 BOM 会让 PowerShell 把首行注释当成命令报错
    text = f.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    out = DST / f.name
    if f.suffix == ".bat":
        out.write_bytes(text.replace("\n", "\r\n").encode("ascii"))
    else:
        out.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n")
                       .encode("utf-8"))
    print("copied", out.name)
print("POST_BUILD_DONE")
