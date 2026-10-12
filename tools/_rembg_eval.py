"""Evaluate rembg AI segmentation on the trickiest existing cells.

Crops blink_raw cell0 (face/horns/metal) and tap3 curled frame, runs
rembg (u2net, then isnet if available), composites on magenta, and
writes side-by-side QA images.
"""
import os
import sys

os.environ.setdefault("U2NET_HOME", r"C:\git-repo\pet\tools\.u2net")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
from rembg import new_session, remove

ROOT = r"C:\git-repo\pet"
MAGENTA = (200, 30, 160, 255)


def composite(rgba: Image.Image) -> Image.Image:
    bg = Image.new("RGBA", rgba.size, MAGENTA)
    bg.alpha_composite(rgba)
    return bg


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "u2net"
    print("creating session", model, flush=True)
    sess = new_session(model)

    jobs = [
        ("blink0", os.path.join(ROOT, "assets", "sheets", "blink_raw.png"),
         None, 0),
        ("tap3c", os.path.join(ROOT, "assets", "sheets", "tap3_draft.png"),
         None, 6),
    ]
    outs = []
    for tag, path, _, idx in jobs:
        sheet = Image.open(path).convert("RGB")
        w, h = sheet.size
        n = max(1, round(w / h))
        cw = w // n
        cell = sheet.crop((idx * cw + 2, 0, (idx + 1) * cw - 2, h))
        print("rembg on", tag, cell.size, flush=True)
        out = remove(cell, session=sess, post_process_mask=True)
        qa = composite(out.convert("RGBA"))
        p = os.path.join(ROOT, "tools", f"_rembg_{tag}_{model}.png")
        qa.save(p)
        outs.append(p)
        print("saved", p, flush=True)


if __name__ == "__main__":
    main()
