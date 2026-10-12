"""One-off: rebuild tap3_draft.png = ref04 first 4 cells (yawn sequence,
wings visible) + new sleep strip 3 cells (wings draped like a blanket)."""
import os

import numpy as np
from PIL import Image

ROOT = r"C:\git-repo\pet"
DRAFTS = os.path.join(ROOT, "assets", "sheets", "ref_drafts")
SHEETS = os.path.join(ROOT, "assets", "sheets")
CELL_W = 500
CYAN = (0, 170, 200)


def cyan_passable(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    df = mx - mn
    hue = np.zeros_like(mx)
    mr, mg, mb = mx == r, mx == g, mx == b
    with np.errstate(invalid="ignore"):
        hue[mr] = ((g - b)[mr] / df[mr]) % 6
        hue[mg] = ((b - r)[mg] / df[mg]) + 2
        hue[mb] = ((r - g)[mb] / df[mb]) + 4
    hue /= 6
    sat = np.where(mx > 0, df / np.maximum(mx, 1e-6), 0)
    spread = np.minimum(g, b) - r
    cyan_hue = (hue > 0.40) & (hue < 0.60) & (sat > 0.12) & (mx > 0.16)
    cyan_tint = (spread > 0.04)
    bright_floor = (mx > 0.55) & (df < 0.22) & (np.minimum(g, b) > r + 0.02)
    return cyan_hue | cyan_tint | bright_floor


def cyan_band_bounds(a, min_w=15):
    colbg = cyan_passable(a).all(0)
    bounds, i, W = [], 0, a.shape[1]
    while i < W:
        if colbg[i]:
            j = i
            while j < W and colbg[j]:
                j += 1
            center = (i + j) // 2
            if j - i >= min_w and 80 < center < W - 80:
                bounds.append(center)
            i = j
        else:
            i += 1
    return bounds


def cells_at(img, bounds):
    edges = [0] + bounds + [img.width]
    out = []
    for i in range(len(edges) - 1):
        x0, x1 = edges[i] + 2, edges[i + 1] - 2
        if x1 > x0:
            out.append(img.crop((x0, 0, x1, img.height)))
    return out


def fixed_equal_cells(img, n):
    w = img.width
    return [img.crop((k * w // n + 8, 0, (k + 1) * w // n - 8, img.height))
            for k in range(n)]


def assemble(cells, h, out_name):
    out = Image.new("RGB", (CELL_W * len(cells), h), CYAN)
    for i, c in enumerate(cells):
        tile = Image.new("RGB", (CELL_W, h), CYAN)
        tile.paste(c, ((CELL_W - c.width) // 2, 0))
        out.paste(tile, (i * CELL_W, 0))
    out.save(os.path.join(SHEETS, out_name))
    print(out_name, out.size)


old = Image.open(os.path.join(DRAFTS, "ref04_sleep.png")).convert("RGB")
old_cells = cells_at(old, cyan_band_bounds(np.asarray(old).astype(np.float32) / 255.0))
print("old cells:", len(old_cells))
new = Image.open(os.path.join(SHEETS, "tap3_sleep_raw.png")).convert("RGB")
new_cells = fixed_equal_cells(new, 3)
# new cells are nearly square: shrink to 470 high so ~15px cyan margins
# remain on both sides of each 500px tile -> guaranteed cut gaps
new_cells = [c.resize((int(c.width * 470 / c.height), 470), Image.LANCZOS)
             for c in new_cells]
# 0-3: stand / yawn / yawn / sit-drowsy (wings visible);
# then drowsy sit wings-spread -> blanket curl -> deep sleep
picked = old_cells[:4] + new_cells
assemble(picked, old.height, "tap3_draft.png")
print("tap3 frames:", len(picked))
