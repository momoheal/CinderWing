"""Assemble cleaned drafts from the external reference strips (v3, cyan screen).

True layouts (measured on the cyan re-makes):
- ref06 fire: 3x3 grid (9 square cells), row-major:
    0 stand, 1 small flame, 2 big fire up-right, 3 small flame,
    4 roaring horizontal fire, 5 crouched dying flame,
    6 small flame, 7 open-mouth flame, 8 back view (dropped).
  tap1 keeps [0, 1, 4, 2, 3, 6, 7, 5] -> 8 (ignite -> roar -> die down).
- ref03 bite (re-made strip): middle airborne frames cross cell borders;
  tap2 keeps wind-up frames 0..2 (mirrored to face right) + dedicated
  contained-fire lunge + mirrored ground-fire recovery -> 5.
- ref04 sleep: 8 frames at cyan-gap bands; keep 0..6 (drop the last
  snot-bubble ball) -> 7.
- ref08 happy: 5 even frames; keep [2,3,4] (big smile -> excited ->
  head-up cheer) -> 3.
Each selected frame is centered onto a uniform CELL_W tile for fixed cuts.
"""
import os

import numpy as np
from PIL import Image

ROOT = r"C:\git-repo\pet"
DRAFTS = os.path.join(ROOT, "assets", "sheets", "ref_drafts")
SHEETS = os.path.join(ROOT, "assets", "sheets")
CELL_W = 500
CYAN = (0, 170, 200)


def cyan_passable(a):
    """Boolean mask of cyan-screen / cyan-tinted bright backdrop pixels."""
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
            # ignore edge bands; cells_at seeds the edges itself
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
    out = []
    for k in range(n):
        x0 = k * w // n + 8
        x1 = (k + 1) * w // n - 8
        out.append(img.crop((x0, 0, x1, img.height)))
    return out


def grid_cells(img, rows, cols, h):
    """Split an even rows x cols grid; each cell resized to h x h tiles."""
    cw, ch = img.width // cols, img.height // rows
    out = []
    for ry in range(rows):
        for cx in range(cols):
            cell = img.crop((cx * cw + 6, ry * ch + 6,
                             (cx + 1) * cw - 6, (ry + 1) * ch - 6))
            out.append(cell.resize((h, h), Image.LANCZOS))
    return out


def assemble(cells, h, out_name):
    out = Image.new("RGB", (CELL_W * len(cells), h), CYAN)
    for i, c in enumerate(cells):
        tile = Image.new("RGB", (CELL_W, h), CYAN)
        tile.paste(c, ((CELL_W - c.width) // 2, 0))
        out.paste(tile, (i * CELL_W, 0))
    out.save(os.path.join(SHEETS, out_name))
    print(out_name, out.size)


# ref06: 3x3 grid -> tap1 fire breath (ignite, roar, die down)
img = Image.open(os.path.join(DRAFTS, "ref06_fireB.png")).convert("RGB")
cells = grid_cells(img, 3, 3, 400)
print("ref06 cells:", len(cells))
assemble([cells[i] for i in [0, 1, 4, 2, 3, 6, 7, 5]], 400, "tap1_draft.png")

# ref03 (re-made strip): explicit background-gap bands measured on disk.
# Frames 0..2 are the wind-up (stand, crouch+spark, crouch lower) but face
# left; they are mirrored to face right toward the lunge. The airborne /
# landing frames in the middle have wings spanning across cell boundaries
# and are unusable, so the climax is the dedicated contained-fire lunge
# frame (faces right). The last tile is the crouched ground-fire recovery,
# mirrored to face right as well. -> 5 frames.
img = Image.open(os.path.join(DRAFTS, "ref03_bite.png")).convert("RGB")
raw_bounds = [(44, 396), (440, 846), (883, 1275), (3543, 3960)]
raw_cells = [img.crop((x0, 0, x1, img.height)) for x0, x1 in raw_bounds]
windup = [raw_cells[0]] + [c.transpose(Image.FLIP_LEFT_RIGHT) for c in raw_cells[1:3]]
recovery = raw_cells[3].transpose(Image.FLIP_LEFT_RIGHT)
lunge = Image.open(os.path.join(SHEETS, "tap2_lunge_raw.png")).convert("RGB")
ls = min(CELL_W / lunge.width, img.height / lunge.height)
lunge = lunge.resize((int(lunge.width * ls), int(lunge.height * ls)), Image.LANCZOS)
assemble(windup + [lunge] + [recovery], img.height, "tap2_draft.png")

# ref04: cyan bands (8 frames)
img = Image.open(os.path.join(DRAFTS, "ref04_sleep.png")).convert("RGB")
a = np.asarray(img).astype(np.float32) / 255.0
cells = cells_at(img, cyan_band_bounds(a))
print("ref04 cells:", len(cells))
assemble(cells[:7], img.height, "tap3_draft.png")

# ref08: 5 even frames; celebration escalates big smile -> excited -> cheer
img = Image.open(os.path.join(DRAFTS, "ref08_happy.png")).convert("RGB")
cells = fixed_equal_cells(img, 5)
print("ref08 cells:", len(cells))
assemble([cells[i] for i in [2, 3, 4]], img.height, "happy_draft.png")
