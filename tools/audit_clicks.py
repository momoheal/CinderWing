"""Drive the live pet with PostMessage clicks and capture each reaction.

Sequence:
  head click (tap1) -> grab
  body click (tap2) -> grab
  long press 800ms  -> sleep (tap3 hold) -> grab
  click to wake     -> grab
"""
import ctypes
import sys
import time
from ctypes import wintypes

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
hwnd_holder = {}


def find(h, l):
    t = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(h, t, 256)
    if user32.IsWindowVisible(h) and t.value == "CinderWing":
        hwnd_holder["h"] = h
    return True


def grab(hwnd, out):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, 2)

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                    ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                    ("biClrImportant", ctypes.c_uint32)]

    bi = BIH(biSize=40, biWidth=w, biHeight=-h, biPlanes=1, biBitCount=32, biCompression=0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).save(out)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)


def click(hwnd, x, y, hold=0.12):
    lp = (y << 16) | (x & 0xFFFF)
    user32.PostMessageW(hwnd, 0x201, 1, lp)
    time.sleep(hold)
    user32.PostMessageW(hwnd, 0x202, 0, lp)


def press_release(hwnd, x, y, hold):
    lp = (y << 16) | (x & 0xFFFF)
    user32.PostMessageW(hwnd, 0x201, 1, lp)
    time.sleep(hold)
    user32.PostMessageW(hwnd, 0x202, 0, lp)


user32.EnumWindows(WNDENUMPROC(find), 0)
hwnd = hwnd_holder.get("h")
if not hwnd:
    print("pet not found")
    sys.exit(1)

time.sleep(1.0)
click(hwnd, 120, 55)            # head -> tap1 fire roar
time.sleep(0.9)
grab(hwnd, "tools/_react_tap1.png")
time.sleep(2.5)                 # let tap1 finish -> idle

click(hwnd, 120, 180)           # body -> tap2 lunge bite
time.sleep(0.7)
grab(hwnd, "tools/_react_tap2.png")
time.sleep(2.5)

press_release(hwnd, 120, 150, 0.9)  # long press -> sleep
time.sleep(1.2)
grab(hwnd, "tools/_react_sleep.png")

time.sleep(1.0)
click(hwnd, 120, 150)           # wake
time.sleep(0.9)
grab(hwnd, "tools/_react_wake.png")
print("ok")
