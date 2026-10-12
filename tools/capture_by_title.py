"""按窗口标题抓取桌宠（打包后的 exe 进程名不是 pythonw，故按标题抓）。"""
import ctypes
import sys
from ctypes import wintypes
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
TITLE = "CinderWing"
out = sys.argv[1] if len(sys.argv) > 1 else "tools/_m4_pet.png"

hwnd_found = []
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                     wintypes.LPARAM)


def cb(hwnd, _):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    if buf.value == TITLE and user32.IsWindowVisible(hwnd):
        hwnd_found.append(hwnd)
    return True


user32.EnumWindows(EnumWindowsProc(cb), 0)
assert hwnd_found, "pet window not found"
hwnd = hwnd_found[0]
r = wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(r))
w, h = r.right - r.left, r.bottom - r.top
print("hwnd", hwnd, "rect", (r.left, r.top, w, h))

hdc_screen = user32.GetDC(0)
hdc = gdi32.CreateCompatibleDC(hdc_screen)
bmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
gdi32.SelectObject(hdc, bmp)
print("PrintWindow", user32.PrintWindow(hwnd, hdc, 2))


class BIH(ctypes.Structure):
    _fields_ = [(n, t) for n, t in [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD)]]


bih = BIH()
bih.biSize = ctypes.sizeof(bih)
bih.biWidth = w; bih.biHeight = -h; bih.biPlanes = 1; bih.biBitCount = 32
buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1)
# 透明区在 PrintWindow 下是黑底，垫品红便于观察
bg = Image.new("RGBA", (w, h), (200, 30, 160, 255))
bg.alpha_composite(img)
bg.convert("RGB").save(out)
print("saved", out)
