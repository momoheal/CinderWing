"""Step-by-step diagnostic for drag via SendInput."""
import ctypes
import ctypes.wintypes as wt
import time

u = ctypes.windll.user32
# become per-monitor DPI aware so GetWindowRect returns physical coords
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
except Exception:
    u.SetProcessDPIAware()

hwnd = None
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


def cb(h, l):
    global hwnd
    s = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(h, s, 256)
    if s.value == "小死亡之翼桌宠":
        hwnd = h
    return True


u.EnumWindows(EnumProc(cb), 0)


def rect():
    r = wt.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


print("physical rect", rect())
r = wt.RECT()
u.GetWindowRect(hwnd, ctypes.byref(r))
cx, cy = (r.left + r.right) // 2, (r.top + r.bottom) // 2
u.SetCursorPos(cx, cy)
time.sleep(0.2)
pt = wt.POINT()
u.GetCursorPos(ctypes.byref(pt))
print("cursor after set:", pt.x, pt.y, "expected", cx, cy)
wfp = u.WindowFromPoint(wt.POINT(pt.x, pt.y))
print("window under cursor:", wfp, "pet hwnd:", hwnd)

INPUT_MOUSE = 0
MOVE, LEFTDOWN, LEFTUP = 0x0001, 0x0002, 0x0004


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_void_p)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("mi", MOUSEINPUT)]


def send(flags, dx=0, dy=0):
    i = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dx, dy, 0, flags, 0, None))
    return u.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))


print("send down ret", send(LEFTDOWN))
time.sleep(0.2)
print("async L button state:", u.GetAsyncKeyState(0x01))
for k in range(4):
    print("move ret", send(MOVE, -45, -25))
    time.sleep(0.15)
    u.GetCursorPos(ctypes.byref(pt))
    print("  cursor", pt.x, pt.y, "rect", rect())
send(LEFTUP)
print("final rect", rect())
