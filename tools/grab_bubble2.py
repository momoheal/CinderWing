"""M5 抓图：按进程抓宠物进程的所有 Qt 窗口（含较高的决策气泡）。"""
import ctypes
import subprocess
import sys
from ctypes import wintypes

from PIL import Image

ps = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
     "Where-Object { $_.CommandLine -like '*app.main*' } | "
     "Select-Object -ExpandProperty ProcessId"],
    capture_output=True, text=True)
pids = {int(x) for x in ps.stdout.split() if x.strip().isdigit()}
print("pids", pids)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
hits = []
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def cb(hwnd, l):
    if user32.IsWindowVisible(hwnd):
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        t = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, t, 256)
        c = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, c, 256)
        if pid.value in pids:
            hits.append((hwnd, r.left, r.top, r.right - r.left,
                         r.bottom - r.top, t.value, c.value))
    return True


user32.EnumWindows(EnumProc(cb), 0)
for h in hits:
    print(h)

target = [x for x in hits if x[5] != "小死亡之翼桌宠"]
if not target:
    print("no bubble window")
    sys.exit(1)

hwnd, x, y, w, h = target[0][:5]
hdc0 = user32.GetDC(0)
hdc = gdi32.CreateCompatibleDC(hdc0)
bmp = gdi32.CreateCompatibleBitmap(hdc0, w, h)
gdi32.SelectObject(hdc, bmp)
print("PrintWindow", user32.PrintWindow(hwnd, hdc, 2), w, h)


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
bih.biWidth = w
bih.biHeight = -h
bih.biPlanes = 1
bih.biBitCount = 32
buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
out = sys.argv[1] if len(sys.argv) > 1 else r"tools\_m5_bubble_ask.png"
Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).save(out)
print("saved", out)
