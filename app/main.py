"""程序入口：把 QApplication、音效、桌宠窗口、托盘组装起来并启动。"""
import ctypes
import logging
import os
import sys
from datetime import datetime

from PySide6.QtWidgets import QApplication

from app import paths
from app.bubble import Bubble
from app.pet_window import PetWindow
from app.sfx import Sfx
from app.tray import build_tray_icon

LOG_PATH = paths.log_path()


def setup_logging():
    logging.basicConfig(
        filename=os.path.abspath(LOG_PATH),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )

    def hook(exc_type, exc, tb):
        logging.getLogger("pet").error(
            "未捕获异常", exc_info=(exc_type, exc, tb)
        )

    sys.excepthook = hook


def already_running() -> bool:
    """单实例保护：同名互斥量已存在说明宠物已在运行。"""
    mutex_name = "Global\\CinderWing_SingleInstance_v1"
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, mutex_name)
    return kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def main() -> int:
    setup_logging()
    log = logging.getLogger("pet")
    log.info("启动 %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if already_running():
        log.info("已有实例运行，退出")
        return 0
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关窗口不退出，常驻托盘

    sfx = Sfx()
    window = PetWindow(sfx)
    bubble = Bubble(window)
    window.bubble = bubble
    bubble.state_changed.connect(window.on_bubble_state)
    bubble.jump_requested.connect(window.jump_to_task)
    tray = build_tray_icon(app, window, sfx, bubble)
    window.tray_icon = tray

    window.show()
    if "--sim" in sys.argv:
        from app import activator
        activator.SIMULATE = True
        from app.dev_sim import simulate
        simulate(window)
    else:
        # 真实任务事件源：轮询豆包工作客户端，把任务状态播报给气泡
        from app.task_source import DoubaoTaskSource
        source = DoubaoTaskSource(
            bubble,
            on_event=bubble.notify,
            on_progress=bubble.update_progress,
            parent=app,
        )
        window.task_source = source
    log.info("进入事件循环")
    code = app.exec()
    log.info("事件循环结束 code=%s", code)
    return code


if __name__ == "__main__":
    sys.exit(main())
