"""M3：把用户带到豆包工作里的指定会话。

首选方式是豆包工作注册的系统协议（实测见 docs/M3讲解.md）：

    doubaowork://doubaowork-chat/chat/<conversation_id>

前端 bundle 里会话路由就是 "/chat/<conversation_id>"，协议由
DoubaoWork.exe 的 --open-url 处理，会在已运行的客户端里直接切到
该会话（无需新开窗口、无需登录）。

协议调不起来时，退而求其次：把豆包工作主窗口抢到前台。
"""
import ctypes
import logging
import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

EXE_KEYWORD = "DoubaoWork.exe"
PROTO_TMPL = "doubaowork://doubaowork-chat/chat/{cid}"

# --sim 演示模式：只记录"将要跳转"，不真的拉起客户端
SIMULATE = False

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
OpenProcess = kernel32.OpenProcess
QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
CloseHandle = kernel32.CloseHandle
ShowWindow = user32.ShowWindow
SetForegroundWindow = user32.SetForegroundWindow
GetWindowThreadProcessId.restype = ctypes.c_uint32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_RESTORE = 9


def _process_path(pid):
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_uint32(1024)
        if QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
    finally:
        CloseHandle(h)
    return ""


def _find_doubaowork_hwnd():
    found = []

    def cb(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_uint32()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        path = _process_path(pid.value)
        if path and os.path.basename(path) == EXE_KEYWORD:
            n = GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            GetWindowTextW(hwnd, buf, n + 1)
            title = buf.value
            # 只要有标题的顶层窗口（主窗口），跳过无标题的工具/渲染窗口
            if title.strip():
                found.append((hwnd, title))
        return True

    EnumWindows(EnumWindowsProc(cb), 0)
    return found[0][0] if found else None


def bring_to_front():
    """兜底：把豆包工作主窗口恢复并置前。成功返回 True。"""
    hwnd = _find_doubaowork_hwnd()
    if not hwnd:
        logging.warning("activator: DoubaoWork window not found")
        return False
    ShowWindow(hwnd, SW_RESTORE)
    ok = bool(SetForegroundWindow(hwnd))
    logging.info("activator: bring_to_front hwnd=%s ok=%s", hwnd, ok)
    return ok


def activate_conversation(conversation_id, section_id=None):
    """打开豆包工作并定位到指定会话。

    conversation_id 必须是数字串（真实会话 id）；演示用的假 id 直接忽略，
    避免 --sim 时打开错误页面。
    """
    cid = str(conversation_id or "").strip()
    if not cid.isdigit():
        logging.info("activator: skip non-numeric conversation id %r", cid)
        return False
    uri = PROTO_TMPL.format(cid=cid)
    # section_id 目前前端路由未发现公开格式，/chat/<cid> 已会落到该会话
    # 最新段落；保留参数位，后续校准后再拼 query。
    if SIMULATE:
        logging.info("activator: [SIM] would open %s", uri)
        return True
    ok = QDesktopServices.openUrl(QUrl(uri))
    logging.info("activator: openUrl %s -> %s", uri, ok)
    if not ok:
        return bring_to_front()
    return True
