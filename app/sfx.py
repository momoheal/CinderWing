"""音效管理：按名字播放 WAV；enabled 由托盘菜单的音效开关控制。"""
import os

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

from app import paths

SFX_FILES = {
    "tap1": "tap1_roar.wav",
    "tap2": "tap2_lunge.wav",
    "tap3": "tap3_yawn.wav",
    "drag": "drag_boing.wav",
    "click": "click.wav",
}


class Sfx:
    def __init__(self):
        self.enabled = True
        root = paths.asset_path("sfx")
        self.effects = {}
        for key, fn in SFX_FILES.items():
            e = QSoundEffect()
            e.setSource(QUrl.fromLocalFile(os.path.join(root, fn)))
            e.setVolume(0.8)
            self.effects[key] = e

    def play(self, key):
        if self.enabled:
            self.effects[key].play()
