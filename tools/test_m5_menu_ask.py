"""M5 离屏 UI 测试：右键菜单 + 决策选项气泡（不拉起真实客户端）。"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from app import activator
activator.SIMULATE = True
from app.bubble import Bubble

app = QApplication([])

calls = []


class FakeSfx:
    enabled = True

    def play(self, name):
        pass


class FakePlayer:
    def __init__(self):
        self.played = None

    def stop(self):
        pass

    def play(self, name):
        self.played = name


class FakePet:
    def __init__(self, bubble):
        self.bubble = bubble
        self.sfx = FakeSfx()
        self.player = FakePlayer()
        self._sleeping = False
        self._long_pressed = False
        self._press_pos = None
        self._dragging = False
        self._sleep_timer = app.findChild(QObjectSafe := type("T", (), {}))

    def geometry(self):
        from PySide6.QtCore import QRect
        return QRect(100, 500, 240, 240)

    def screen(self):
        return app.primaryScreen()

    def hide(self):
        self.hidden = True


# FakePet 里偷懒的属性在下面用真实 PetWindow 更稳；这里只测 Bubble 部分，
# PetWindow 菜单逻辑单独用轻量替身验证。
from PySide6.QtCore import QTimer


class FakePetWindow:
    def __init__(self, bubble):
        self.bubble = bubble
        self.sfx = FakeSfx()
        self.player = FakePlayer()
        self._sleeping = False
        self._long_pressed = False
        self._press_pos = None
        self._dragging = False
        self._drop_timer = QTimer()
        self._sleep_timer = QTimer()
        self.hidden = False
        self.quit = False

    def hide(self):
        self.hidden = True

    def _enter_sleep(self):
        self.slept = True

    def geometry(self):
        from PySide6.QtCore import QRect
        return QRect(100, 500, 240, 240)

    def screen(self):
        return app.primaryScreen()


bubble = Bubble(FakePetWindow(None))
fake_win = FakePetWindow(bubble)
bubble.pet = fake_win
bubble.jump_requested.connect(lambda k: calls.append(k))


def pump(ms=50):
    QTest.qWait(ms)


ASK = {"questions": [{
    "title": "需要你确认：如何处理这 12 个重复素材？",
    "type": 1,
    "options": [
        {"id": "opt-keep", "label": "全部保留，只在清单里标注重复"},
        {"id": "opt-move", "label": "移到「待确认」文件夹"},
        {"id": "opt-delete", "label": "直接删除重复文件"},
    ],
    "allow_text": True,
}]}

# 1) WAITING + 选项：渲染出 3 个选项按钮 + 1 个自定义回答按钮
bubble.notify("WAITING", "需要你确认：如何处理这 12 个重复素材？",
              "t1", "整理素材", 30, "38446069288761602", None, ask=ASK)
pump()
bubble.grab()
assert len(bubble._opt_rects) == 4, f"应有 4 个按钮，实际 {len(bubble._opt_rects)}"
print("OK 1: 选择题渲染 3 选项 + 自定义回答按钮")

# 2) 决策气泡不自动隐藏（sticky）
assert not bubble._hide_timer.isActive(), "WAITING 决策气泡应常驻"
print("OK 2: WAITING 决策气泡常驻不自动隐藏")

# 3) 点选项按钮 → jump_requested
calls.clear()
r = bubble._opt_rects[1]
QTest.mouseClick(bubble, Qt.LeftButton, Qt.NoModifier, r.center())
pump()
assert calls == ["t1"], f"点选项应跳转，实际 {calls}"
print("OK 3: 点选项按钮 -> jump_requested(t1)")

# 4) 自由文本题（无 options）：渲染一个“打开豆包输入回答”按钮
bubble2 = Bubble(FakePetWindow(None))
bubble2.notify("WAITING", "请描述你看到的跳转结果", "t2", "深链测试",
               None, "38444948096752642", None,
               ask={"questions": [{
                   "title": "请描述你看到的跳转结果",
                   "type": 3, "options": [], "allow_text": True}]})
pump()
bubble2.grab()
assert len(bubble2._opt_rects) == 1, f"自由文本应有 1 个按钮，实际 {len(bubble2._opt_rects)}"
print("OK 4: 自由文本题渲染单一“去豆包回答”按钮")

# 5) show_panel：有任务时展开；无任务时返回 False
bubble3 = Bubble(FakePetWindow(None))
assert bubble3.show_panel() is False
bubble3.notify("PROGRESS", "进行中", "x", "任务X", 20,
               "38444948096752642", None)
pump()
assert bubble3.show_panel() is True and bubble3._expanded
print("OK 5: show_panel 空态 False / 有任务展开面板")

# 6) 右键菜单动作：手动互动播帧、隐藏、待命提示
from app.pet_window import PetWindow
win = PetWindow.__new__(PetWindow)
# 直接验证菜单回调方法在真实类上存在
assert hasattr(PetWindow, "contextMenuEvent")
assert hasattr(PetWindow, "_open_progress_panel")
assert hasattr(PetWindow, "_manual_play")
print("OK 6: PetWindow 右键菜单相关方法齐备")

# 7) Task.ask_buttons 展平逻辑
t = bubble.tasks["t1"]
btns = t.ask_buttons()
assert [b[0] for b in btns] == ["option", "option", "option", "free"], btns
print("OK 7: ask_buttons 展平顺序正确")

print("\n全部通过 ✔")
