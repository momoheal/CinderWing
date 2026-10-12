"""M6 真机验证：右键宠物 → 键盘下移到「更换形象」→ 右箭头展开子菜单 → 截图。"""
import ctypes
import subprocess
import time
from ctypes import wintypes

from PIL import ImageGrab

user32 = ctypes.windll.user32


def find_pet():
    rect = None

    def cb(hwnd, l):
        nonlocal rect
        if user32.IsWindowVisible(hwnd):
            t = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, t, 256)
            if t.value == "CinderWing":
                r = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                rect = (r.left, r.top, r.right, r.bottom)
        return True

    EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(EnumProc(cb), 0)
    return rect


pet_rect = find_pet()
print("pet rect", pet_rect)
if pet_rect is None:
    raise SystemExit("没有找到运行中的宠物窗口")
x1, y1, x2, y2 = pet_rect
cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

user32.SetCursorPos(cx, cy)
time.sleep(0.4)
user32.mouse_event(0x0008, 0, 0, 0, 0)  # RIGHTDOWN
time.sleep(0.08)
user32.mouse_event(0x0010, 0, 0, 0, 0)  # RIGHTUP
time.sleep(1.0)

KEYEVENTF_KEYUP = 0x0002
VK_DOWN, VK_RIGHT = 0x28, 0x27


def tap(vk, hold=0.12):
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(hold)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.25)


tap(VK_DOWN)   # 逗逗它（打开时首项已选中）
tap(VK_DOWN)   # 更换形象
tap(VK_RIGHT, 0.3)  # 展开子菜单
time.sleep(0.5)
tap(VK_DOWN)   # 在子菜单里下移一格，证明子菜单已展开
time.sleep(0.8)

img = ImageGrab.grab(all_screens=True)
out = r"C:\git-repo\pet\tools\_m6_skin_menu.png"
img.save(out)
print("saved", out, img.size)
