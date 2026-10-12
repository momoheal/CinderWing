"""Click the bubble center (toggle multi-task panel), then grab it."""
import ctypes
from ctypes import wintypes
import sys, time
import subprocess
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
out = sys.argv[1]

ps = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-Process pythonw | Where-Object { $_.Path -like 'C:\\git-repo\\pet*' } | "
     "Select-Object -ExpandProperty Id"],
    capture_output=True, text=True)
pids = {int(x) for x in ps.stdout.split() if x.strip().isdigit()}

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
hits = []

def cb(hwnd, l):
    if user32.IsWindowVisible(hwnd):
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        w0, h0 = r.right - r.left, r.bottom - r.top
        if cls.value.startswith("Qt") and w0 > 200 and h0 < 320:
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            if title.value != "小死亡之翼桌宠":
                hits.append((hwnd, r.left, r.top, w0, h0))
    return True

user32.EnumWindows(EnumWindowsProc(cb), 0)
print("bubble candidates", hits)
hwnd, x, y, w, h = hits[0]
cx, cy = w // 2, h // 2
lp = (cy << 16) | (cx & 0xFFFF)
user32.PostMessageW(hwnd, 0x201, 1, lp)  # WM_LBUTTONDOWN
user32.PostMessageW(hwnd, 0x202, 0, lp)  # WM_LBUTTONUP
time.sleep(1.2)

r = wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(r))
w, h = r.right - r.left, r.bottom - r.top
print("after click", w, h)

hdc_screen = user32.GetDC(0)
hdc = gdi32.CreateCompatibleDC(hdc_screen)
bmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
gdi32.SelectObject(hdc, bmp)
user32.PrintWindow(hwnd, hdc, 2)

class BIH(ctypes.Structure):
    _fields_ = [(n, t) for n, t in [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD)]]

bih = BIH(); bih.biSize = ctypes.sizeof(bih)
bih.biWidth = w; bih.biHeight = -h; bih.biPlanes = 1; bih.biBitCount = 32
buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).save(out)
gdi32.DeleteObject(bmp); gdi32.DeleteDC(hdc); user32.ReleaseDC(0, hdc_screen)
print("saved", out)
