"""Capture the live pet (and its bubble) straight from the window handles.

Uses PrintWindow(PW_RENDERFULLCONTENT) so layered / translucent top-most
windows are captured without relying on screen-coordinate math.

Usage: python capture_pet.py <out_png>
"""
import ctypes
import sys
from ctypes import wintypes

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()

PW_RENDERFULLCONTENT = 2


class BIH(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


def print_window(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return None
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    ok = user32.PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT)
    bi = BIH(biSize=40, biWidth=w, biHeight=-h, biPlanes=1,
             biBitCount=32, biCompression=0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    return img, (r.left, r.top, r.right, r.bottom)


# enumerate visible top-level windows of every pythonw process in the pet venv
pet_hwnd = None
others = []
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def cb(h, l):
    t = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(h, t, 256)
    if user32.IsWindowVisible(h) and t.value == "CinderWing":
        others.append((h, t.value))
        global pet_hwnd
        pet_hwnd = h
    return True


user32.EnumWindows(WNDENUMPROC(cb), 0)
if pet_hwnd is None:
    print("pet window not found")
    sys.exit(1)

pet_img, pet_rect = print_window(pet_hwnd)
l, t, r, b = pet_rect

# canvas: pet rect plus generous room above for the bubble
CW, CH = 700, 760
canvas = Image.new("RGBA", (CW, CH), (200, 30, 160, 255))
# pet placed near bottom center
px = CW // 2 - (r - l) // 2
py = CH - (b - t) - 20
canvas.alpha_composite(pet_img, (px, py))

# find the bubble: top-level visible window of the same thread, no title,
# whose rect is just above / overlapping the pet
tid = user32.GetWindowThreadProcessId(pet_hwnd, None)


def cb2(h, l):
    if not user32.IsWindowVisible(h) or h == pet_hwnd:
        return True
    if user32.GetWindowThreadProcessId(h, None) != tid:
        return True
    rr = wintypes.RECT()
    user32.GetWindowRect(h, ctypes.byref(rr))
    # bubble sits above the pet and is horizontally close to it
    if (rr.bottom > t - 500 and rr.top < t + 80
            and abs((rr.left + rr.right) // 2 - (l + r) // 2) < 500):
        res = print_window(h)
        if res:
            bimg, br = res
            bx = px + (br[0] + br[2]) // 2 - (l + r) // 2 - bimg.width // 2
            by = py - (t - br[1]) - bimg.height + 6
            canvas.alpha_composite(bimg, (bx, by))
            print("bubble at", br)
    return True


bubble_hwnd = None
user32.EnumWindows(WNDENUMPROC(cb2), 0)
canvas.save(sys.argv[1])
print("saved", sys.argv[1], "pet", pet_rect)
