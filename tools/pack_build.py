"""通用角色包构建工具（M6）：把 AI 生成的动作条图加工成可换装的角色包。

输入（一个文件夹）约定：
    <sheets_dir>/
        sheets.json            可选，显式声明每张条图怎么切：
            {"idle":  {"file": "idle.png",  "cells": 8},
             "blink": {"file": "blink.png", "cells": 5},
             "tap1":  {"file": "tap1.png",  "cells": 8},
             ...}
        idle.png blink.png tap1.png tap2.png tap3.png drag.png
        happy.png talk.png scratch.png
    没有 sheets.json 时：
      - 文件名可写成 idle_8.png（末尾数字=格数）
      - 否则按"每格近似正方形"自动推断格数（横向条图 cols≈宽/高）

加工流程（与内置小龙同一套成熟工艺）：
    逐格裁剪 → rembg/u2net 语义抠像（免疫幕布溢色，不会在身上挖白块）
    → 连通区清理 → 透明底裁边 → 等比缩放到 205 高、脚对齐 256 画布
    → 输出 frames/<动作>/NN.png
    → 品红底质检拼图 qa_<id>.png（禁止用白底，高光会被误判）

用法：
    python tools/pack_build.py <sheets_dir> --id my-pet --name "我的宠物"
    python tools/pack_build.py sheets/ --id pup --name 小狗 --author me --out D:\\packs

环境变量 U2NET_HOME 指向 u2net 模型目录（首次运行 rembg 会自动下载）。
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_frames as bf  # 复用 ai_cutout / place / u2net 会话
from app import packs as packs_mod

ANIMS = packs_mod.ANIMS
CANVAS = 256
TARGET_H = 205
SIDE = 24
MAGENTA = (200, 30, 160, 255)


def guess_cells(im: Image.Image, name: str, info: dict | None) -> tuple[int, int]:
    """返回 (cols, rows)。"""
    if info:
        cells = int(info.get("cells", 1))
        rows = int(info.get("rows", 1))
        cols = cells // rows
        if cells % rows:
            cols += 1
        return max(1, cols), rows
    # 文件名末尾数字：idle_8.png
    base = os.path.splitext(name)[0]
    if "_" in base and base.rsplit("_", 1)[1].isdigit():
        return int(base.rsplit("_", 1)[1]), 1
    w, h = im.size
    ratio = w / max(h, 1)
    cols = max(1, round(ratio)) if ratio >= 1.3 else 1
    return cols, 1


def build(sheets_dir: str, pack_id: str, name: str, author: str,
          out_root: str | None) -> dict:
    sheets_dir = os.path.abspath(sheets_dir)
    mapping = {}
    sj = os.path.join(sheets_dir, "sheets.json")
    if os.path.isfile(sj):
        with open(sj, encoding="utf-8") as f:
            mapping = json.load(f)

    # 找到每个动作对应的源文件
    sources: dict[str, tuple[str, dict]] = {}
    for anim in ANIMS:
        info = mapping.get(anim) if isinstance(mapping.get(anim), dict) else None
        if info and info.get("file"):
            p = os.path.join(sheets_dir, info["file"])
            if os.path.isfile(p):
                sources[anim] = (p, info)
                continue
        # 自动匹配：<anim>*.png，优先文件名完全匹配
        cands = [f for f in os.listdir(sheets_dir)
                 if f.lower().startswith(anim) and f.lower().endswith(".png")]
        if cands:
            cands.sort(key=lambda f: (len(f), f))
            sources[anim] = (os.path.join(sheets_dir, cands[0]), info)

    missing = [a for a in ANIMS if a not in sources]
    if missing:
        print(f"[提示] 缺少 {len(missing)} 套动作，运行时将回退默认形象："
              f"{', '.join(missing)}")

    out_parent = out_root or str(packs_mod.packs_dir())
    pack_dir = os.path.join(out_parent, pack_id)
    frames_dir = os.path.join(pack_dir, "frames")
    os.makedirs(pack_dir, exist_ok=True)

    stats = {}
    for anim in ANIMS:
        if anim not in sources:
            continue
        path, info = sources[anim]
        sheet = Image.open(path).convert("RGB")
        cols, rows = guess_cells(sheet, os.path.basename(path), info)
        cw, ch = sheet.width // cols, sheet.height // rows
        anchor = (info or {}).get("anchor", "bottom")
        target_h = int((info or {}).get("target_h", TARGET_H))
        side = int((info or {}).get("side", SIDE))
        out_dir = os.path.join(frames_dir, anim)
        os.makedirs(out_dir, exist_ok=True)
        n = 0
        coverages = []
        for r in range(rows):
            for c in range(cols):
                cell = sheet.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
                cut = bf.ai_cutout(cell)
                frame, _ = bf.place(cut, target_h, CANVAS, side, anchor)
                # 空帧（某格留白）跳过
                alpha = __import__("numpy").asarray(frame)[..., 3]
                coverage = int((alpha > 40).sum())
                if coverage < 400:
                    print(f"[跳过] {anim} 第 {n} 格几乎为空")
                else:
                    frame.save(os.path.join(out_dir, f"{n:02d}.png"))
                    coverages.append(coverage)
                    n += 1
        stats[anim] = coverages
        print(f"[完成] {anim}: {n} 帧 <- {os.path.basename(path)} "
              f"({cols}列x{rows}行)")

    # pack.json
    meta = {
        "id": pack_id,
        "name": name,
        "author": author,
        "version": 1,
        "generator": "pack_build 1.0",
        "fps": {a: packs_mod.DEFAULT_FPS[a] for a in ANIMS},
    }
    with open(os.path.join(pack_dir, "pack.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # preview.png：idle 第一帧贴深色圆角底
    idle0 = os.path.join(frames_dir, "idle", "00.png")
    if os.path.isfile(idle0):
        bg = Image.new("RGBA", (256, 256), (38, 38, 44, 255))
        bg.alpha_composite(Image.open(idle0).convert("RGBA"))
        bg.save(os.path.join(pack_dir, "preview.png"))

    qa_path = make_qa_sheet(frames_dir, pack_id, out_parent)
    warn(stats)
    print(f"\n角色包已生成：{pack_dir}")
    print(f"质检图（品红底）：{qa_path}")
    print("在宠物右键菜单「更换形象」里即可看到并切换。")
    return {"pack_dir": pack_dir, "qa": qa_path, "missing": missing}


def make_qa_sheet(frames_dir: str, pack_id: str, out_parent: str) -> str:
    """每套动作一行，品红底拼接，肉眼查白块/缺帧/越界。"""
    cell = 132
    rows = []
    for anim in ANIMS:
        d = os.path.join(frames_dir, anim)
        if not os.path.isdir(d):
            continue
        files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        rows.append((anim, files))
    if not rows:
        return ""
    width = max(len(files) for _, files in rows) * cell + 90
    height = len(rows) * cell + 10
    sheet = Image.new("RGBA", (width, height), MAGENTA)
    draw = ImageDraw.Draw(sheet)
    for i, (anim, files) in enumerate(rows):
        y = i * cell
        draw.text((6, y + cell // 2 - 6), anim, fill=(255, 255, 255, 255))
        for j, fn in enumerate(files):
            im = Image.open(os.path.join(frames_dir, anim, fn)).convert("RGBA")
            im = im.resize((cell - 8, cell - 8))
            sheet.alpha_composite(im, (80 + j * cell + 4, y + 4))
    qa = os.path.join(out_parent, f"qa_{pack_id}.png")
    sheet.convert("RGB").save(qa)
    return qa


def warn(stats: dict) -> None:
    """帧间不透明像素占比异常时提示（可能抠像残缺/多了东西）。"""
    for anim, cov in stats.items():
        if len(cov) < 2:
            continue
        med = sorted(cov)[len(cov) // 2]
        for i, c in enumerate(cov):
            if c < 0.45 * med:
                print(f"[警告] {anim} 第{i}帧内容明显偏少（{c} vs 中位 {med}），"
                      f"请在品红质检图上确认是否抠缺")
            if c > 1.7 * med:
                print(f"[警告] {anim} 第{i}帧内容明显偏多（{c} vs 中位 {med}），"
                      f"可能混入了邻格或背景")


def main():
    ap = argparse.ArgumentParser(description="构建桌宠角色包")
    ap.add_argument("sheets_dir", help="放 9 套动作条图的文件夹")
    ap.add_argument("--id", required=True, help="角色包英文 id（文件夹名）")
    ap.add_argument("--name", required=True, help="显示名，如 小烬翼")
    ap.add_argument("--author", default="", help="作者名（可选）")
    ap.add_argument("--out", default=None, help="输出的 packs 父目录，"
                                                "默认写入宠物的形象文件夹")
    args = ap.parse_args()
    build(args.sheets_dir, args.id, args.name, args.author, args.out)


if __name__ == "__main__":
    main()
