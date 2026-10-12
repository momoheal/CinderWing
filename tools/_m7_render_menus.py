"""M7 生成开源 README 用的干净菜单截图（离屏渲染，不依赖屏幕抓拍）：
- docs/images/m7-context-menu.png  完整右键菜单
- docs/images/m7-skin-menu.png     更换形象子菜单
- docs/images/m7-play-menu.png     逗逗它子菜单
- docs/images/m7-pet-hero.png      小龙形象主图（深色圆角底）
"""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.pet_window import PetWindow  # noqa: E402
from app.paths import asset_path  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "images")

app = QApplication([])
win = PetWindow(None)
menu, _ = win._build_context_menu()


def render(widget, path):
    widget.setAttribute(Qt.WA_DontShowOnScreen)
    widget.show()
    app.processEvents()
    widget.resize(widget.sizeHint())
    app.processEvents()
    pm = widget.grab()
    widget.close()
    pm.save(path)
    print("saved", path, pm.size().width(), pm.size().height())


render(menu, os.path.join(OUT, "m7-context-menu.png"))
render(menu._skin_submenu, os.path.join(OUT, "m7-skin-menu.png"))

# 逗逗它子菜单
play = next(a for a in menu.actions() if a.text() == "逗逗它")
render(play.menu(), os.path.join(OUT, "m7-play-menu.png"))

# 主图：idle 首帧贴深色圆角底
frame = QPixmap(asset_path(os.path.join("frames", "idle", "00.png")))
hero = QPixmap(320, 320)
hero.fill(Qt.transparent)
p = QPainter(hero)
p.setRenderHint(QPainter.Antialiasing)
p.setBrush(QColor("#2b2b30"))
p.setPen(Qt.NoPen)
p.drawRoundedRect(2, 2, 316, 316, 24, 24)
p.drawPixmap(32, 32, 256, 256, frame)
p.end()
hero.save(os.path.join(OUT, "m7-pet-hero.png"))
print("saved hero")
