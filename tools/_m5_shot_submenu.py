"""M5：展开“逗逗它”子菜单并截图。"""
import ctypes
import time
from ctypes import wintypes

from PIL import Image, ImageGrab

user32 = ctypes.windll.user32

pet_rect = None
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def cb(hwnd, l):
    global pet_rect
    if user32.IsWindowVisible(hwnd):
        t = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, t, 256)
        if t.value == "小死亡之翼桌宠":
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            pet_rect = (r.left, r.top, r.right, r.bottom)
    return True


user32.EnumWindows(EnumProc(cb), 0)
x1, y1, x2, y2 = pet_rect
cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

user32.SetCursorPos(cx, cy)
time.sleep(0.3)
user32.mouse_event(0x0008, 0, 0, 0, 0)
time.sleep(0.08)
user32.mouse_event(0x0010, 0, 0, 0, 0)
time.sleep(0.8)
# 菜单第 2 项“逗逗它”大约在右键点下方 55px；右移展开子菜单
user32.SetCursorPos(cx + 30, cy + 55)
time.sleep(0.8)
img = ImageGrab.grab(all_screens=True)
vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
box = (cx - 200 - vx, cy - 60 - vy, cx + 360 - vx, cy + 360 - vy)
img.crop(box).save(r"C:\git-repo\pet\tools\_m5_submenu.png")
print("saved", box)
# Esc 关掉菜单
user32.keybd_event(0x1B, 0, 0, 0)
user32.keybd_event(0x1B, 0, 2, 0)
