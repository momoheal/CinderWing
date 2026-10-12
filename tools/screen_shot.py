"""DPI-aware full-screen capture via ctypes BitBlt (includes CAPTUREBLT so layered windows show).

Usage:
  python screen_shot.py <out_png>                 # full virtual screen
  python screen_shot.py <out_png> <x> <y> <w> <h> # crop a physical-coordinate rectangle
"""
import ctypes
import sys

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()

SM_X, SM_Y, SM_W, SM_H = 76, 77, 78, 79
vx = user32.GetSystemMetrics(SM_X)
vy = user32.GetSystemMetrics(SM_Y)
vw = user32.GetSystemMetrics(SM_W)
vh = user32.GetSystemMetrics(SM_H)

SRCCOPY, CAPTUREBLT = 0x00CC0020, 0x40000000

screen_dc = user32.GetDC(0)
mem_dc = gdi32.CreateCompatibleDC(screen_dc)
bmp = gdi32.CreateCompatibleBitmap(screen_dc, vw, vh)
gdi32.SelectObject(mem_dc, bmp)
gdi32.BitBlt(mem_dc, 0, 0, vw, vh, screen_dc, vx, vy, SRCCOPY | CAPTUREBLT)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


bi = BITMAPINFOHEADER(biSize=40, biWidth=vw, biHeight=-vh, biPlanes=1,
                       biBitCount=32, biCompression=0)
buf = ctypes.create_string_buffer(vw * vh * 4)
gdi32.GetDIBits(mem_dc, bmp, 0, vh, buf, ctypes.byref(bi), 0)
img = Image.frombuffer("RGBA", (vw, vh), buf, "raw", "BGRA", 0, 1)

# cleanup
gdi32.DeleteObject(bmp)
gdi32.DeleteDC(mem_dc)
user32.ReleaseDC(0, screen_dc)

if len(sys.argv) >= 6:
    x, y, w, h = map(int, sys.argv[2:6])
    img = img.crop((x, y, x + w, y + h))
img.save(sys.argv[1])
print(f"saved {sys.argv[1]} from virtual {vx},{vy} {vw}x{vh}")
