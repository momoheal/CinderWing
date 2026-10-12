import ctypes
from ctypes import wintypes

u = ctypes.windll.user32
u.SetProcessDPIAware()
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
pet_pid = ctypes.c_ulong()


def cb0(h, l):
    t = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(h, t, 256)
    if t.value == '小死亡之翼桌宠':
        u.GetWindowThreadProcessId(h, ctypes.byref(pet_pid))
    return True


u.EnumWindows(WNDENUMPROC(cb0), 0)
lines = [f"pid {pet_pid.value}"]


def cb(h, l):
    pid = ctypes.c_ulong()
    tid = u.GetWindowThreadProcessId(h, ctypes.byref(pid))
    if pid.value == pet_pid.value and u.IsWindowVisible(h):
        r = wintypes.RECT()
        u.GetWindowRect(h, ctypes.byref(r))
        t = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(h, t, 256)
        lines.append(f"hwnd={h} tid={tid} title={t.value!r} rect=({r.left},{r.top},{r.right},{r.bottom})")
    return True


u.EnumWindows(WNDENUMPROC(cb), 0)
with open(r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.sessions\38444948096752642\agents\m_0cwpwYn3kVx\wins.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
