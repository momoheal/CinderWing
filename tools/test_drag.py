"""Real-input drag test: grab the pet, drag it, hold, release; captures happen outside."""
import ctypes
import ctypes.wintypes as wt
import time

u = ctypes.windll.user32

# find pet
hwnd = None
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


def cb(h, l):
    global hwnd
    s = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(h, s, 256)
    if s.value == "CinderWing":
        hwnd = h
    return True


u.EnumWindows(EnumProc(cb), 0)
r = wt.RECT()
u.GetWindowRect(hwnd, ctypes.byref(r))
# logical -> physical on main screen (150%)
cx = int((r.left + r.right) / 2 * 1.5)
cy = int((r.top + r.bottom) / 2 * 1.5)
print("start physical", cx, cy)

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
    u.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))


u.SetCursorPos(cx, cy)
time.sleep(0.3)
send(LEFTDOWN)
time.sleep(0.25)
# drag up-left in steps
for i in range(8):
    send(MOVE, -45, -25)
    time.sleep(0.05)
time.sleep(0.3)
print("HOLD - capture now")
time.sleep(1.0)  # window for external screenshot
send(LEFTUP)
print("released")
time.sleep(0.4)
r2 = wt.RECT()
u.GetWindowRect(hwnd, ctypes.byref(r2))
print("end logical rect", r2.left, r2.top, r2.right, r2.bottom)
