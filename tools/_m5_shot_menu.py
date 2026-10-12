"""M5 真机验证：在宠物窗口上右键，截全屏看右键菜单。"""
import ctypes
import subprocess
import time
from ctypes import wintypes

from PIL import ImageGrab

user32 = ctypes.windll.user32

ps = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
     "Where-Object { $_.CommandLine -like '*app.main*' } | "
     "Select-Object -ExpandProperty ProcessId"],
    capture_output=True, text=True)
pids = {int(x) for x in ps.stdout.split() if x.strip().isdigit()}
print("pids", pids)

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
print("pet rect", pet_rect)
x1, y1, x2, y2 = pet_rect
cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

user32.SetCursorPos(cx, cy)
time.sleep(0.4)
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
time.sleep(0.08)
user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
time.sleep(1.2)

img = ImageGrab.grab(all_screens=True)
out = r"C:\git-repo\pet\tools\_m5_context_menu.png"
img.save(out)
print("saved", out, img.size)
