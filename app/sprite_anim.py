"""精灵播放器：加载某个角色包的序列帧，用 QTimer 按固定节奏换帧。

零基础说明：
- 每"一帧"是一张透明 PNG；快速连续地换图，就成了动画（翻页动画原理）。
- loop=True 表示循环播放（待机用）；动作动画播一遍就停，并发出 finished 信号。
- 角色包里缺少某套动作时，自动用内置默认形象的同名动作顶上。
"""
import os

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPixmap

from app import packs as packs_mod


class SpritePlayer(QObject):
    frame_changed = Signal(QPixmap)
    finished = Signal(str)

    def __init__(self, pack=None, fallback=None):
        super().__init__()
        self.fallback = fallback or packs_mod.builtin_pack()
        self.pack = None
        self.frames = {}
        self.fps_map = dict(packs_mod.DEFAULT_FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.set_pack(pack or packs_mod.selected_pack())
        self.name = None
        self.idx = 0
        self.loop = False
        self.hold = None      # loop only the first N frames (drag: 0..4)
        self.hold_last = False  # after playing once, freeze on the last frame

    def set_pack(self, pack) -> None:
        """切换角色包：重新装载 9 套帧，缺失动作回退默认形象。"""
        self.pack = pack
        self.frames = {}
        fps = dict(packs_mod.DEFAULT_FPS)
        fps.update(pack.fps)
        self.fps_map = fps
        for anim in packs_mod.ANIMS:
            files = pack.frame_files(anim)
            if not files and not pack.is_builtin:
                files = self.fallback.frame_files(anim)
            if files:
                self.frames[anim] = [QPixmap(f) for f in files]
        self.name = None
        self.idx = 0
        self.timer.stop()

    def play(self, name, loop=False, hold=None, hold_last=False):
        self.name = name
        self.idx = 0
        self.loop = loop
        self.hold = hold
        self.hold_last = hold_last
        self.timer.start(int(1000 / self.fps_map.get(name, 12)))
        self._show()

    def show_frame(self, name, idx):
        """只显示某一帧的静态画面：不算"正在播放动画"，
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
