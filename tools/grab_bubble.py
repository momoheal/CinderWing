"""Grab the bubble HWND alone via PrintWindow."""
import ctypes
from ctypes import wintypes
import sys
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

out = sys.argv[1]
pid0 = None
import subprocess
# find pythonw pid running from project dir
ps = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-Process pythonw | Where-Object { $_.Path -like 'C:\\git-repo\\pet*' } | "
     "Select-Object -ExpandProperty Id"],
    capture_output=True, text=True)
pids = {int(x) for x in ps.stdout.split() if x.strip().isdigit()}
print("pids", pids)

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect
PrintWindow = user32.PrintWindow

hits = []

def cb(hwnd, l):
    if IsWindowVisible(hwnd):
        r = wintypes.RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        w0, h0 = r.right - r.left, r.bottom - r.top
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 256)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if cls.value.startswith("Qt") or pid.value in pids:
            hits.append((hwnd, r.left, r.top, w0, h0, title.value, cls.value, pid.value))
    return True

EnumWindows(EnumWindowsProc(cb), 0)
for hit in hits:
    print(hit)

# grab the widest short window near the pet top (the bubble)
bub = [x for x in hits if x[3] > 200 and x[4] < 200 and x[5] != 'CinderWing']
if not bub:
    print("no bubble"); sys.exit(1)
hwnd, x, y, w, h = bub[0][:5]
hdc_screen = user32.GetDC(0)
hdc = gdi32.CreateCompatibleDC(hdc_screen)
bmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
gdi32.SelectObject(hdc, bmp)
ok = PrintWindow(hwnd, hdc, 2)
print("PrintWindow", ok, w, h)

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [(n, t) for n, t in [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD)]]

bih = BITMAPINFOHEADER()
bih.biSize = ctypes.sizeof(bih)
bih.biWidth = w; bih.biHeight = -h; bih.biPlanes = 1; bih.biBitCount = 32
bih.biCompression = 0
buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1)
img.save(out)
gdi32.DeleteObject(bmp); gdi32.DeleteDC(hdc); user32.ReleaseDC(0, hdc_screen)
print("saved", out)
