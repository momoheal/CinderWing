"""精灵播放器：加载 assets/frames 下的序列帧，用 QTimer 按固定节奏换帧。

零基础说明：
- 每"一帧"是一张透明 PNG；快速连续地换图，就成了动画（翻页动画原理）。
- loop=True 表示循环播放（待机用）；动作动画播一遍就停，并发出 finished 信号。
"""
import os

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPixmap

from app import paths

ROOT = paths.asset_path("frames")

FPS = {
    "idle": 2, "blink": 9, "tap1": 9, "tap2": 9, "tap3": 7, "drag": 2,
    "happy": 9, "talk": 8, "scratch": 7,
}


class SpritePlayer(QObject):
    frame_changed = Signal(QPixmap)
    finished = Signal(str)

    def __init__(self):
        super().__init__()
        self.frames = {}
        for name in sorted(os.listdir(ROOT)):
            d = os.path.join(ROOT, name)
            if os.path.isdir(d):
                self.frames[name] = [
                    QPixmap(os.path.join(d, f)) for f in sorted(os.listdir(d))
                ]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.name = None
        self.idx = 0
        self.loop = False
        self.hold = None  # loop only the first N frames (drag: 0..4)
        self.hold_last = False  # after playing once, freeze on the last frame

    def play(self, name, loop=False, hold=None, hold_last=False):
        self.name = name
        self.idx = 0
        self.loop = loop
        self.hold = hold
        self.hold_last = hold_last
        self.timer.start(int(1000 / FPS.get(name, 12)))
        self._show()

    def show_frame(self, name, idx):
        """只显示某一帧的静态画面：不算“正在播放动画”，
        否则待机时 player.name 一直非空，呼吸/眨眼/睡眠判定全部失效。"""
        self.timer.stop()
        self.idx = idx
        self.loop = False
        self.name = None
        self.frame_changed.emit(self.frames[name][idx])

    def stop(self):
        self.timer.stop()
        self.name = None

    def _tick(self):
        self.idx += 1
        seq = self.frames[self.name]
        limit = self.hold if self.hold is not None else len(seq)
        if self.idx >= limit:
            if self.loop:
                self.idx = 0
            elif self.hold_last:
                # freeze forever on the final frame (sleeping pet)
                self.idx = limit - 1
                self.timer.stop()
                self._show()
                return
            else:
                self.timer.stop()
                name = self.name
                self.name = None
                self.finished.emit(name)
                return
        self._show()

    def _show(self):
        self.frame_changed.emit(self.frames[self.name][self.idx])
