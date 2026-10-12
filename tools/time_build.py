import sys, time
sys.path.insert(0, r"C:\git-repo\pet\tools")
import numpy as np
from PIL import Image
import build_frames as bf

# correctness: tiny grid
m = np.array([
    [1,0,0,0,1,1],
    [1,1,0,0,1,0],
    [0,1,0,1,1,0],
    [0,0,0,1,0,0],
    [1,0,0,0,0,1],
], bool)
flood = bf._flood(m, *m.shape)
# border-connected: (0,0)(1,0)(1,1)(2,1); (0,4)(0,5)(1,4)(2,4)(2,3)(3,3); (4,0); (4,5)
expect = {(0,0),(1,0),(1,1),(2,1),(0,4),(0,5),(1,4),(2,4),(2,3),(3,3),(4,0),(4,5)}
got = set(zip(*np.nonzero(flood)))
assert got == expect, (got, expect)
a = np.zeros((5,6,3), np.float32)
lab, info = bf._label_stats(m, a, 5, 6)
assert len(info) == 4, len(info)
areas = sorted(st["area"] for st in info.values())
assert areas == [1,1,4,6], areas
print("correctness ok")

sheet = Image.open(r"C:\git-repo\pet\assets\sheets\tap1_draft.png").convert("RGB")
w, h = sheet.size
cell = sheet.crop((2*w//8 + 2, 0, 3*w//8 - 2, h))
a = np.asarray(cell).astype(np.float32) / 255.0
t=time.time(); masks = bf.bg_masks(a); print("bg_masks", round(time.time()-t,2))
t=time.time(); alpha = bf.chroma_alpha(a, *masks[1:]); print("chroma", round(time.time()-t,2))
t=time.time(); out = bf.finish_alpha(a, alpha, *masks[1:6], True, False); print("finish", round(time.time()-t,2))
