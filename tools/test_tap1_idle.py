"""Head-click the live pet (tap1), capture; then sample idle frames for blink."""
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
assert hwnd

SHOT = (
    r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default"
    r"\.doubaowork\agent_mode\workspace\.sessions\38444948096752642"
    r"\agents\m_0cwpwYn3kVx"
)
PY = r"C:\git-repo\pet\.venv\Scripts\python.exe"
SS = r"C:\git-repo\pet\tools\screen_shot.py"


def shoot(name, x=4900, y=900, w=640, h=720):
    subprocess.run([PY, SS, SHOT + "\\" + name, str(x), str(y), str(w), str(h)])


def click(cx, cy, hold=0.05):
    lp = (cy << 16) | cx
    u.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, lp)
    time.sleep(hold)
    u.PostMessageW(hwnd, WM_LBUTTONUP, 0, lp)


# head click -> tap1 (client coords physical; head zone y < 151)
click(180, 80)
time.sleep(0.45)
shoot("live_tap1_a.png")
time.sleep(0.7)
shoot("live_tap1_b.png")

# wait for rest, then sample idle to catch a blink/breath cycle
time.sleep(3)
for i in range(5):
    shoot(f"live_idle_{i}.png")
    time.sleep(1.2)
print("done")
