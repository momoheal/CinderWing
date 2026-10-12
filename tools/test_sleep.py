"""Long-press the live pet via PostMessage, then capture sleep state twice."""
import ctypes
import subprocess
import time
from ctypes import wintypes

u = ctypes.windll.user32
u.SetProcessDPIAware()

WM_LBUTTONDOWN, WM_LBUTTONUP = 0x201, 0x202

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
hwnd = None


def find(h, lp):
    global hwnd
    n = u.GetWindowTextLengthW(h)
    if n:
        b = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, b, n + 1)
        if b.value == "小死亡之翼桌宠":
            hwnd = h
    return True


u.EnumWindows(WNDENUMPROC(find), 0)
assert hwnd, "pet window not found"

rc = wintypes.RECT()
u.GetClientRect(hwnd, ctypes.byref(rc))
cx, cy = (rc.right - rc.left) // 2, (rc.bottom - rc.top) // 2
lp = (cy << 16) | cx
u.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, lp)
time.sleep(0.8)
u.PostMessageW(hwnd, WM_LBUTTONUP, 0, lp)

SHOT = (
    r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default"
    r"\.doubaowork\agent_mode\workspace\.sessions\38444948096752642"
    r"\agents\m_0cwpwYn3kVx"
)
PY = r"C:\git-repo\pet\.venv\Scripts\python.exe"
SS = r"C:\git-repo\pet\tools\screen_shot.py"

time.sleep(1.2)
subprocess.run([PY, SS, SHOT + r"\sleep1.png", "4900", "950", "640", "700"])
time.sleep(1.6)
subprocess.run([PY, SS, SHOT + r"\sleep2.png", "4900", "950", "640", "700"])
print("sleep test done")
