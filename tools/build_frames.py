"""Slice sprite sheets into transparent, normalized frame PNGs (v0.8).

Matting is AI semantic segmentation (rembg/u2net) instead of chroma keying:
it is immune to cyan light spill on the dragon's rim-lit scales, which was
the root cause of the recurring white/transparent patches inside the body
(per-pixel hue rules cannot separate backdrop-coloured light on the subject
from the backdrop itself). The chroma keyer is kept only as a fallback.

Special builds:
  idle  - 8-frame Live2D-style breathing synthesized from the open-eye base
          (feet anchored; chest/shoulders rise, belly swells, head follows
          a fraction; seamless sine loop).
  blink - 5 frames where ONLY the eye region changes (open frame blended
          against an AI closed-eye frame inside tight feathered masks), so
          the head can never turn.
"""
import os
from collections import deque

import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = r"C:\git-repo\pet"
SHEETS = os.path.join(ROOT, "assets", "sheets")
OUT = os.path.join(ROOT, "assets", "frames")

SESSION = new_session("u2net")

# name, raw files, frames per part, anchor, target height, canvas,
# side margin, fixed equal grid
CONFIGS = [
    ("tap1", ["tap1_a_raw.png", "tap1_b_raw.png", "tap1_c_raw.png"],
     [3, 3, 2], "bottom", 205, 256, 24, True),
    ("tap2", ["tap2_draft.png"], [5], "bottom", 205, 256, 24, True),
    ("tap3", ["tap3_draft.png"], [7], "bottom", 205, 256, 24, True),
    ("drag", ["drag_a_raw.png", "drag_b_raw.png"], [3, 3],
     "center", 190, 256, 32, True),
    ("happy", ["happy_draft.png"], [3], "bottom", 205, 256, 24, True),
    ("talk", ["talk2_raw.png"], [6], "bottom", 205, 256, 36, True),
    ("scratch", ["scratch_raw.png"], [4], "bottom", 205, 256, 36, True),
]

CANVAS = 256
FEET_Y = CANVAS - 18


# ---------------------------------------------------------------- cutout

def _label_components(mask):
    """4-connected labels + per-component stats (run-based, no scipy)."""
    H, W = mask.shape
    padded = np.hstack([np.zeros((H, 1), bool), mask, np.zeros((H, 1), bool)]).ravel()
    d = np.diff(np.concatenate(([0], padded.view(np.int8), [0])))
    run_starts = np.nonzero(d == 1)[0]
    run_ends = np.nonzero(d == -1)[0]
    row_of = run_starts // (W + 2)
    x0_of = run_starts % (W + 2) - 1
    x1_of = run_ends % (W + 2) - 2

    raw = np.zeros((H, W), np.int32)
    parent = []

    def new_id():
        i = len(parent)
        parent.append(i)
        return i

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    rows = [[] for _ in range(H)]
    for k in range(len(run_starts)):
        rows[row_of[k]].append(k)
    run_label = [0] * len(run_starts)
    for y in range(H):
        cur = rows[y]
        prev = rows[y - 1] if y > 0 else []
        pi = 0
        for k in cur:
            x0, x1 = int(x0_of[k]), int(x1_of[k])
            lid = new_id()
            run_label[k] = lid
            raw[y, x0:x1 + 1] = lid + 1
            while pi < len(prev) and x1_of[prev[pi]] < x0:
                pi += 1
            pj = pi
            while pj < len(prev) and x0_of[prev[pj]] <= x1:
                union(lid, run_label[prev[pj]])
                pj += 1

    labels = np.zeros((H, W), np.int32)
    info = {}
    if parent:
        roots = np.array([find(i) for i in range(len(parent))], np.int32)
        uniq = np.unique(roots)
        remap = np.zeros(len(parent) + 1, np.int32)
        remap[uniq] = np.arange(1, len(uniq) + 1)
        nz = raw > 0
        labels[nz] = remap[roots[raw[nz] - 1]]

    flat = labels.ravel()
    on = flat > 0
    ys, xs = np.mgrid[0:H, 0:W]
    yon, xon = ys.ravel()[on], xs.ravel()[on]
    lab = flat[on]
    order = np.argsort(lab, kind="stable")
    lab_s, ys_s, xs_s = lab[order], yon[order], xon[order]
    counts = np.bincount(lab_s)
    border = set(labels[0, :].tolist()) | set(labels[-1, :].tolist()) \
        | set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
    border.discard(0)
    for c in range(1, len(counts)):
        m = lab_s == c
        info[c] = {
            "area": int(counts[c]),
            "touches": c in border,
            "cy": float(ys_s[m].mean()),
            "maxy": int(ys_s[m].max()),
        }
    return labels, info


def ai_cutout(cell: Image.Image, keep_detached: bool = True) -> Image.Image:
    """AI matte + conservative component cleanup. Returns RGBA."""
    out = remove(cell.convert("RGB"), session=SESSION,
                 post_process_mask=True).convert("RGBA")
    arr = np.array(out)
    alpha = arr[..., 3]
    hard = alpha > 127
    labels, info = _label_components(hard)
    # The body (with attached fire/wings/tail) is by far the largest
    # component. Keep it plus detached INTERIOR embers; drop everything
    # else that touches a cell border (separator slivers, floor smears,
    # and fire plumes bleeding in from a neighbouring cell).
    biggest = max(info, key=lambda c: info[c]["area"])
    drop = np.zeros(hard.shape, bool)
    for c, st in info.items():
        comp = labels == c
        if c == biggest:
            continue
        if st["touches"] or st["area"] < 24:
            drop |= comp
    alpha[drop] = 0

    # dangling sheets sometimes include a thin "string" the generator drew
    # above the head: a horizontal opening of the top 30% strip removes
    # narrow vertical protrusions while wings/head survive.
    hard2 = alpha > 127
    cut = int(hard2.shape[0] * 0.30)
    strip = hard2[:cut]
    K = 7
    p = np.pad(strip, ((0, 0), (K, K)), mode="constant")
    ero = np.minimum.reduce([p[:, K + s:K + s + strip.shape[1]] for s in range(-K, K + 1)])
    pe = np.pad(ero, ((0, 0), (K, K)), mode="constant")
    opened = np.maximum.reduce([pe[:, K + s:K + s + strip.shape[1]] for s in range(-K, K + 1)])
    alpha[:cut] = np.where(opened, alpha[:cut], 0)
    arr[..., 3] = alpha

    # u2net post-processing can fill an ENCLOSED backdrop pocket (e.g. the
    # gap wrapped by wing + tail + body) with opaque backdrop colour. Clear
    # bright saturated cyan components that do not reach the cell border.
    rr, gg, bb = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
    mx, mn = arr[..., :3].max(2), arr[..., :3].min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    cyan = (arr[..., 3] > 200) & (bb > 125) & (bb - rr > 45) \
        & (gg - rr > 15) & (sat > 0.20)
    clab, cinfo = _label_components(cyan)
    for c, st in cinfo.items():
        if not st["touches"]:
            arr[clab == c, 3] = 0
    return Image.fromarray(arr, "RGBA")


def final_clean(layer: Image.Image, canvas: int) -> Image.Image:
    arr = np.array(layer)
    alpha = arr[..., 3]
    fg = alpha > 20
    hard = alpha > 140
    seen = np.zeros(fg.shape, bool)
    drop_mask = np.zeros(fg.shape, bool)
    H, W = fg.shape
    for sy in range(H):
        for sx in range(W):
            if not fg[sy, sx] or seen[sy, sx]:
                continue
            seen[sy, sx] = True
            q = deque([(sy, sx)])
            pts, hard_n, bottom = [], 0, 0
            while q:
                y, x = q.popleft()
                pts.append((y, x))
                hard_n += int(hard[y, x])
                bottom = max(bottom, y)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and fg[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if (len(pts) < 12 and hard_n < 4) or (len(pts) < 600 and bottom >= canvas - 45):
                for y, x in pts:
                    drop_mask[y, x] = True
    arr[drop_mask, 3] = 0
    return Image.fromarray(arr, "RGBA")


# ------------------------------------------------------------- placement

def place(img: Image.Image, target_h, canvas, side, anchor):
    bb = img.getbbox()
    sub = img.crop(bb)
    f = min(target_h / sub.height, (canvas - side) / sub.width)
    if sub.width * f > canvas - 16:
        f = (canvas - 16) / sub.width
    nw, nh = max(1, int(sub.width * f)), max(1, int(sub.height * f))
    sub = sub.resize((nw, nh), Image.LANCZOS)
    layer = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    if anchor == "bottom":
        layer.paste(sub, ((canvas - nw) // 2, FEET_Y - nh), sub)
        layer.paste((0, 0, 0, 0), (0, canvas - 8, canvas, canvas))
    else:
        layer.paste(sub, ((canvas - nw) // 2, (canvas - nh) // 2), sub)
    return final_clean(layer, canvas), f


# ------------------------------------------------------- breathing v0.8

def body_breath(layer: Image.Image, level: float) -> Image.Image:
    """Live2D-style breath: feet planted, chest/shoulders rise ~3px, belly
    swells ~1.5px, head follows with ~half the lift. Sine-driven, seamless.
    """
    arr = np.asarray(layer).astype(np.float32)
    H, W = arr.shape[:2]
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)

    # vertical lift: 0 at/under feet (y>=224), 1 at shoulders (y<=118)
    v = np.clip((224 - ys) / (224 - 118), 0, 1)
    v = v * v * (3 - 2 * v)          # smoothstep
    head = np.clip((118 - ys) / (118 - 70), 0, 1)  # extra head damp
    lift = level * v * (3.0 - 1.4 * head)          # body 3px, head ~1.6px

    # belly/chest outward swell (gaussian around lower torso); fade it out
    # completely toward/under the feet so toes never slide.
    foot_anchor = np.clip((226 - ys) / (226 - 196), 0, 1)
    gx = np.exp(-(((xs - 128) / 46) ** 2) - (((ys - 168) / 60) ** 2)) * foot_anchor
    swell = level * 1.7 * gx * (xs - 128) / 46.0
    # chest slight upward lift
    gt = np.exp(-(((xs - 128) / 40) ** 2) - (((ys - 140) / 46) ** 2))
    lift = lift + level * 1.1 * gt

    x_src = np.clip(xs - swell, 0, W - 1.001)
    # sampling src from BELOW (y + lift) moves the content UP by lift
    y_src = np.clip(ys + lift, 0, H - 1.001)
    x0, y0 = np.floor(x_src).astype(np.int32), np.floor(y_src).astype(np.int32)
    fx, fy = (x_src - x0)[..., None], (y_src - y0)[..., None]
    x1, y1 = np.clip(x0 + 1, 0, W - 1), np.clip(y0 + 1, 0, H - 1)
    rows = np.arange(H)[:, None]
    top = arr[y0, x0] * (1 - fx) + arr[y0, x1] * fx
    bot = arr[y1, x0] * (1 - fx) + arr[y1, x1] * fx
    out = top * (1 - fy) + bot * fy
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


# ------------------------------------------------------------ blink v0.8

def detect_eyes(rgba_layer):
    """Locate the two eyes automatically: inside the face band they are the
    two largest saturated golden-yellow components (horn lava lives higher).
    Returns soft ellipse parameters on the canvas.
    """
    arr = np.asarray(rgba_layer).astype(np.uint8)
    r, g, b = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
    a = arr[..., 3]
    yellow = (a > 200) & (r > 165) & (g > 105) & (b < 120) \
        & (r - b > 85) & (g - b > 55)
    yellow[:92, :] = False      # horns / crest above the face
    yellow[138:, :] = False     # mouth / belly below the eyes
    yellow[:, :66] = False
    yellow[:, 176:] = False
    lab, info = _label_components(yellow)
    comps = sorted(info.values(), key=lambda s: -s["area"])[:2]
    if len(comps) < 2:
        raise RuntimeError(f"eye detection found {len(comps)} components")
    # component stats lack bbox x; recompute bboxes from labels
    eyes = []
    for st in comps:
        cid = next(c for c, v in info.items() if v is st)
        ys, xs = np.where(lab == cid)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        eyes.append(dict(cx=float((x0 + x1) / 2), cy=float((y0 + y1) / 2),
                         rx=(x1 - x0) / 2 + 5.5, ry=(y1 - y0) / 2 + 4.5))
    eyes.sort(key=lambda e: e["cx"])
    return eyes


def eye_masks(canvas: int, eyes):
    H = W = canvas
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    m = np.zeros((H, W), np.float32)
    for e in eyes:
        d = ((xs - e["cx"]) / e["rx"]) ** 2 + ((ys - e["cy"]) / e["ry"]) ** 2
        m = np.maximum(m, np.clip(1 - d, 0, 1))
    return m[..., None]


def build_blink(open_layer, closed_layer, n=5, eyes=None):
    """Blend closed-eye frame into the open frame inside eye masks only."""
    if eyes is None:
        eyes = detect_eyes(open_layer)
    o = np.asarray(open_layer).astype(np.float32)
    c = np.asarray(closed_layer).astype(np.float32)
    m = eye_masks(o.shape[0], eyes)
    levels = [0.0, 0.55, 1.0, 0.55, 0.0][:n]
    frames = []
    for p in levels:
        blend = o * (1 - m * p) + c * (m * p)
        blend[..., 3] = o[..., 3]  # alpha always from the open frame
        frames.append(Image.fromarray(np.clip(blend, 0, 255).astype(np.uint8), "RGBA"))
    return frames, eyes


# ----------------------------------------------------------------- main

def save_check(name, frames):
    per = (len(frames) + 1) // 2
    check = Image.new("RGBA", (CANVAS * per, CANVAS * 2), (200, 30, 160, 255))
    for i, fr in enumerate(frames):
        check.paste(fr, ((i % per) * CANVAS, (i // per) * CANVAS), fr)
    check.convert("RGB").save(os.path.join(SHEETS, f"{name}_cut_check.png"))


def main():
    only = None
    import sys
    if len(sys.argv) > 1:
        only = set(sys.argv[1:])

    # ---- special: idle (breathing) + blink (eye blend) share one base ----
    if only is None or "idle" in only or "blink" in only:
        sheet = Image.open(os.path.join(SHEETS, "blink_raw.png")).convert("RGB")
        w, h = sheet.size
        open_cell = sheet.crop((2, 0, w // 5 - 2, h))
        open_cut = ai_cutout(open_cell)
        open_layer, f_open = place(open_cut, 205, CANVAS, 36, "bottom")

        # align the closed-eye frame EXACTLY to the open frame: same placed
        # height, same foot line, horizontally centred on its own bbox.
        ob = open_layer.getbbox()
        h_open = ob[3] - ob[1]
        closed_cut = ai_cutout(
            Image.open(os.path.join(SHEETS, "blink_closed_raw.png")).convert("RGB"))
        cb = closed_cut.getbbox()
        csub = closed_cut.crop(cb)
        cf = h_open / csub.height
        csub = csub.resize((max(1, int(csub.width * cf)), h_open), Image.LANCZOS)
        closed_layer = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
        closed_layer.paste(csub, ((CANVAS - csub.width) // 2, FEET_Y - h_open), csub)
        closed_layer = final_clean(closed_layer, CANVAS)

        eyes = detect_eyes(open_layer)
        print("detected eyes:", eyes)

        if only is None or "blink" in only:
            d = os.path.join(OUT, "blink")
            os.makedirs(d, exist_ok=True)
            for old in os.listdir(d):
                os.remove(os.path.join(d, old))
            frames, _ = build_blink(open_layer, closed_layer, eyes=eyes)
            for i, fr in enumerate(frames):
                fr.save(os.path.join(d, f"{i:02d}.png"))
            save_check("blink", frames)
            print(f"blink: {len(frames)} frames (eye-mask blend)")

        if only is None or "idle" in only:
            d = os.path.join(OUT, "idle")
            os.makedirs(d, exist_ok=True)
            for old in os.listdir(d):
                os.remove(os.path.join(d, old))
            n = 8
            frames = []
            for i in range(n):
                level = 0.5 - 0.5 * np.cos(2 * np.pi * i / n)
                fr = final_clean(body_breath(open_layer, float(level)), CANVAS)
                fr.save(os.path.join(d, f"{i:02d}.png"))
                frames.append(fr)
            save_check("idle", frames)
            print(f"idle: {n} frames (body-rise breathing)")

    # ---- regular sets ----
    for name, raws, parts, anchor, target_h, canvas, side, fixed in CONFIGS:
        if only is not None and name not in only:
            continue
        frames = []
        for raw, n in zip(raws, parts):
            sheet = Image.open(os.path.join(SHEETS, raw)).convert("RGB")
            w, h = sheet.size
            if fixed:
                bounds = [k * w // n for k in range(n + 1)]
            else:
                raise RuntimeError("find_cuts removed; use fixed grids")
            for i in range(n):
                cell = sheet.crop((bounds[i] + 2, 0, bounds[i + 1] - 2, h))
                frames.append(ai_cutout(cell))
        # common scale from median width / p80 height
        boxes = [f.getbbox() for f in frames]
        widths = np.array([b[2] - b[0] for b in boxes])
        heights = np.array([b[3] - b[1] for b in boxes])
        base = min(target_h / np.percentile(heights, 80),
                   (canvas - side) / np.median(widths))
        out_frames = []
        for img in frames:
            bb = img.getbbox()
            sub = img.crop(bb)
            f = base
            if sub.width * f > canvas - 16:
                f = (canvas - 16) / sub.width
            nw, nh = max(1, int(sub.width * f)), max(1, int(sub.height * f))
            sub = sub.resize((nw, nh), Image.LANCZOS)
            layer = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
            if anchor == "bottom":
                layer.paste(sub, ((canvas - nw) // 2, FEET_Y - nh), sub)
                layer.paste((0, 0, 0, 0), (0, canvas - 8, canvas, canvas))
            else:
                layer.paste(sub, ((canvas - nw) // 2, (canvas - nh) // 2), sub)
            out_frames.append(final_clean(layer, canvas))
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for old in os.listdir(d):
            os.remove(os.path.join(d, old))
        for i, fr in enumerate(out_frames):
            fr.save(os.path.join(d, f"{i:02d}.png"))
        save_check(name, out_frames)
        print(f"{name}: {len(out_frames)} frames, base={base:.3f}")


if __name__ == "__main__":
    main()
