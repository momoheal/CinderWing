"""Offscreen preview of the new bubble (compact + expanded + states)."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

from app.bubble import Bubble

app = QApplication([])
pet = QWidget()
pet.setFixedSize(240, 240)
pet.move(400, 700)
pet.show()

b = Bubble(pet)
out = r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.sessions\38444948096752642\agents\m_0cwpwYn3kVx"


def shot(name):
    app.processEvents()
    img = b.grab().toImage()
    from PySide6.QtGui import QImage, QPainter, QColor
    bg = QImage(img.size(), QImage.Format_ARGB32)
    bg.fill(QColor(200, 30, 160))
    p = QPainter(bg)
    p.drawImage(0, 0, img)
    p.end()
    bg.save(os.path.join(out, name))
    print(name, b.width(), b.height())


b.notify("START", "「整理本周设计素材清单」开始了", "a", "整理本周设计素材清单", 0)
b.update_progress("a", 42, "素材已收集完，正在分类…")
b.notify("START", "「导出龙巢宣传页切图」开始了", "b", "导出龙巢宣传页切图", 0)
b.update_progress("b", 18, "正在导出切图…")
shot("bub_compact.png")

b._expanded = True
b._render()
shot("bub_panel.png")

b._expanded = False
b._render()
b.notify("WAITING", "需要你确认：是否删除 12 个重复素材？", "a", "整理本周设计素材清单", 60)
shot("bub_waiting.png")

b.notify("DONE", "「整理本周设计素材清单」完成了", "a", "整理本周设计素材清单", 100)
shot("bub_done.png")
print("ok")
