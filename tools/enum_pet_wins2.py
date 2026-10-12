import ctypes
from ctypes import wintypes

u = ctypes.windll.user32
u.SetProcessDPIAware()
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
pet_pid = ctypes.c_ulong()
pet_hwnd = None


def cb0(h, l):
    global pet_hwnd
    t = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(h, t, 256)
    if t.value == '小死亡之翼桌宠':
        pet_hwnd = h
        u.GetWindowThreadProcessId(h, ctypes.byref(pet_pid))
    return True


u.EnumWindows(WNDENUMPROC(cb0), 0)
pr = wintypes.RECT()
u.GetWindowRect(pet_hwnd, ctypes.byref(pr))
tid = u.GetWindowThreadProcessId(pet_hwnd, None)
lines = [f"pet=({pr.left},{pr.top},{pr.right},{pr.bottom}) tid={tid}"]


def cb(h, l):
    pid = ctypes.c_ulong()
    t2 = u.GetWindowThreadProcessId(h, ctypes.byref(pid))
    if pid.value == pet_pid.value:
        r = wintypes.RECT()
        u.GetWindowRect(h, ctypes.byref(r))
        vis = u.IsWindowVisible(h)
        ti = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(h, ti, 256)
        lines.append(f"hwnd={h} vis={vis} tid={t2} title={ti.value!r} rect=({r.left},{r.top},{r.right},{r.bottom})")
        if vis and h != pet_hwnd:
            ok = (r.bottom > pr.top - 500 and r.top < pr.top + 80
                  and abs((r.left + r.right) // 2 - (pr.left + pr.right) // 2) < 500)
            lines.append(f"   filter_pass={ok}")
    return True


u.EnumWindows(WNDENUMPROC(cb), 0)
with open(r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.sessions\38444948096752642\agents\m_0cwpwYn3kVx\wins2.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
