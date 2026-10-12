"""M3 离屏 UI 测试：气泡点击跳转逻辑（不拉起真实客户端）。"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from app import activator
activator.SIMULATE = True
from app.bubble import Bubble

app = QApplication([])

calls = []


class FakePet:
    def geometry(self):
        from PySide6.QtCore import QRect
        return QRect(100, 500, 240, 240)

    def screen(self):
        return app.primaryScreen()


bubble = Bubble(FakePet())
bubble.jump_requested.connect(lambda k: calls.append(k))


def pump(ms=50):
    QTest.qWait(ms)


# 1) WAITING 任务（有真实会话 id）：点收起状态的气泡应直接请求跳转
bubble.notify("WAITING", "需要你决策：测试任务", "t1", "测试任务", 30,
              "12345678901234568", None)
pump()
bubble.grab()  # 强制走一遍 paintEvent
assert bubble.tasks["t1"].jumpable
QTest.mouseClick(bubble, Qt.LeftButton, Qt.NoModifier, QPoint(30, 30))
pump()
assert calls == ["t1"], f"WAITING 单击应跳转，实际 {calls}"
print("OK 1: WAITING 气泡单击 -> jump_requested(t1)")

# 2) 普通 PROGRESS 气泡：单击应展开面板，不跳转
calls.clear()
bubble.notify("PROGRESS", "任务进行中：测试任务", "t1", "测试任务", 40,
              "12345678901234568", None)
bubble.notify("PROGRESS", "任务进行中：另一个", "t2", "另一个任务", 55,
              "12345678901234567", None)
pump()
QTest.mouseClick(bubble, Qt.LeftButton, Qt.NoModifier, QPoint(30, 30))
pump()
assert calls == [], f"普通状态单击不应跳转，实际 {calls}"
assert bubble._expanded, "应展开多任务面板"
print("OK 2: 普通气泡单击 -> 展开面板，不跳转")

# 3) 面板里点某一行 → 跳转对应任务
bubble.grab()
pump()
rects = bubble._row_rects
assert set(rects) == {"t1", "t2"}, rects
center = rects["t2"].center()
QTest.mouseClick(bubble, Qt.LeftButton, Qt.NoModifier, center)
pump()
assert calls == ["t2"], f"点 t2 行应跳转 t2，实际 {calls}"
print("OK 3: 面板任务行单击 -> jump_requested(t2)")

# 4) 没有会话 id 的任务行不可跳转（点了不 emit）
calls.clear()
bubble.notify("PROGRESS", "任务进行中：无会话", "t3", "无会话任务", 10)
pump()
bubble.grab()
if "t3" in bubble._row_rects:
    QTest.mouseClick(bubble, Qt.LeftButton, Qt.NoModifier,
                     bubble._row_rects["t3"].center())
    pump()
assert calls == [], f"无会话 id 不应跳转，实际 {calls}"
print("OK 4: 无会话 id 的任务行点击不跳转")

# 5) 激活器：假 id 被拒绝，数字 id 在 SIMULATE 下只记录
assert activator.activate_conversation("demo-task-a") is False
assert activator.activate_conversation("12345678901234568") is True
print("OK 5: 激活器 id 校验与 SIMULATE 行为正确")

print("\n全部通过 ✔")
