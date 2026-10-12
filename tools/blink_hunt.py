"""Rapidly grab the pet window during rest to catch a blink clip."""
import ctypes
from ctypes import wintypes
import time, sys
import numpy as np
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
out = sys.argv[1]

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
pet_hwnd = None

def cb(hwnd, l):
    global pet_hwnd
    if user32.IsWindowVisible(hwnd):
        t = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, t, 256)
        if t.value == "CinderWing":
            pet_hwnd = hwnd
    return True

user32.EnumWindows(EnumWindowsProc(cb), 0)
assert pet_hwnd, "pet not found"

r = wintypes.RECT()
user32.GetWindowRect(pet_hwnd, ctypes.byref(r))
w, h = r.right - r.left, r.bottom - r.top

class BIH(ctypes.Structure):
    _fields_ = [(n, t) for n, t in [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD)]]

def grab():
    hdc_screen = user32.GetDC(0)
    hdc = gdi32.CreateCompatibleDC(hdc_screen)
    bmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    gdi32.SelectObject(hdc, bmp)
    user32.PrintWindow(pet_hwnd, hdc, 2)
    bih = BIH(); bih.biSize = ctypes.sizeof(bih)
    bih.biWidth = w; bih.biHeight = -h; bih.biPlanes = 1; bih.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
    img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(hdc); user32.ReleaseDC(0, hdc_screen)
    return img

frames = []
for i in range(26):
    frames.append(grab())
    time.sleep(0.35)

base = np.asarray(frames[0].convert("RGB"), dtype=np.int16)
scores = []
for i, im in enumerate(frames):
    a = np.asarray(im.convert("RGB"), dtype=np.int16)
    scores.append((int(np.abs(a - base).sum()), i))
scores.sort(reverse=True)
picked = sorted(i for _, i in scores[:10])
print("top diffs", scores[:10])
thumbs = [frames[i].resize((180, 180)) for i in picked]
sheet = Image.new("RGB", (180 * len(thumbs), 180), (200, 30, 160))
for k, t in enumerate(thumbs):
    sheet.paste(t, (180 * k, 0), t)
sheet.save(out)
print("saved", out, "frames", picked)
