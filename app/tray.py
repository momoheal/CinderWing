"""系统托盘：小图标 + 右键菜单（显示/隐藏、音效开关、退出）。"""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def _make_tray_icon_image() -> QIcon:
    """代码现画一个 64x64 的小图标（黑圆脸 + 红角 + 金眼）。"""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#2b2b2f"))
    p.drawEllipse(8, 10, 48, 48)
    p.setBrush(QColor("#c0301f"))
    p.drawPolygon([QPointF(20, 14), QPointF(16, 2), QPointF(30, 12)])
    p.drawPolygon([QPointF(44, 14), QPointF(48, 2), QPointF(34, 12)])
    p.setBrush(QColor("#ffd24a"))
    p.drawEllipse(20, 30, 9, 9)
    p.drawEllipse(35, 30, 9, 9)
    p.end()
    return QIcon(pix)


def build_tray_icon(app, window, sfx, bubble=None) -> QSystemTrayIcon:
    menu = QMenu()

    def toggle_visibility():
        if window.isVisible():
            window.hide()
        else:
            window.show()

    toggle_action = QAction("显示 / 隐藏宠物", parent=app)
    toggle_action.triggered.connect(toggle_visibility)

    test_done = QAction("测试：完成通知", parent=app)
    test_flow = QAction("模拟：任务全流程", parent=app)
    if bubble is not None:
        test_done.triggered.connect(
            lambda: bubble.notify("DONE", "「示例任务：整理本周设计素材清单」完成了",
                                  key="demo-done", name="示例任务", progress=100)
        )

        def run_flow():
            from app.dev_sim import simulate
            simulate(window)

        test_flow.triggered.connect(run_flow)

    sound_action = QAction("音效开关", parent=app, checkable=True)
    sound_action.setChecked(bool(sfx and sfx.enabled))
    sound_action.triggered.connect(
        lambda: setattr(sfx, "enabled", sound_action.isChecked())
    )

    progress_action = QAction("任务进度面板", parent=app)
    if bubble is not None:
        progress_action.triggered.connect(
            lambda: window._open_progress_panel())

    quit_action = QAction("退出", parent=app)
    quit_action.triggered.connect(app.quit)

    def _refresh():
        sound_action.setChecked(bool(sfx and sfx.enabled))
    menu.aboutToShow.connect(_refresh)

    menu.addAction(toggle_action)
    menu.addSeparator()
    if bubble is not None:
        menu.addAction(test_done)
        menu.addAction(test_flow)
        menu.addAction(progress_action)
        menu.addSeparator()
    menu.addAction(sound_action)
    menu.addSeparator()
    menu.addAction(quit_action)

    icon = QSystemTrayIcon(_make_tray_icon_image(), parent=app)
    icon.setContextMenu(menu)
    icon.setToolTip("CinderWing")
    icon.activated.connect(
        lambda reason: toggle_visibility()
        if reason == QSystemTrayIcon.DoubleClick else None
    )
    icon.show()
    return icon
