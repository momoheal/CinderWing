"""Compare repeated PrintWindow vs screen BitBlt grabs for live animation."""
import ctypes
from ctypes import wintypes
import time, hashlib
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
pet = None
def cb(hwnd, l):
    global pet
    if user32.IsWindowVisible(hwnd):
        t = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, t, 256)
        if t.value == "CinderWing":
            pet = hwnd
    return True
user32.EnumWindows(EnumWindowsProc(cb), 0)
r = wintypes.RECT()
user32.GetWindowRect(pet, ctypes.byref(r))
x, y, w, h = r.left, r.top, r.right - r.left, r.bottom - r.top
print("rect", x, y, w, h)

class BIH(ctypes.Structure):
    _fields_ = [(n, t) for n, t in [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD)]]

def from_dc(hdc_src, dx, dy):
    hdc = gdi32.CreateCompatibleDC(hdc_src)
    bmp = gdi32.CreateCompatibleBitmap(hdc_src, w, h)
    gdi32.SelectObject(hdc, bmp)
    gdi32.BitBlt(hdc, 0, 0, w, h, hdc_src, x + dx, y + dy, SRCCOPY | CAPTUREBLT)
    bih = BIH(); bih.biSize = ctypes.sizeof(bih)
    bih.biWidth = w; bih.biHeight = -h; bih.biPlanes = 1; bih.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(hdc)
    return buf.raw

def pw():
    hdc_screen = user32.GetDC(0)
    hdc = gdi32.CreateCompatibleDC(hdc_screen)
    bmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    gdi32.SelectObject(hdc, bmp)
    user32.PrintWindow(pet, hdc, 2)
    bih = BIH(); bih.biSize = ctypes.sizeof(bih)
    bih.biWidth = w; bih.biHeight = -h; bih.biPlanes = 1; bih.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(hdc); user32.ReleaseDC(0, hdc_screen)
    return buf.raw

screen_dc = user32.GetDC(0)
for i in range(4):
    a = pw()
    b = from_dc(screen_dc, 0, 0)
    print(i, "pw", hashlib.md5(a).hexdigest()[:8],
          "screen", hashlib.md5(b).hexdigest()[:8])
    time.sleep(1.5)
user32.ReleaseDC(0, screen_dc)
