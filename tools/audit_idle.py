"""Headless timing audit: verify idle ambient behaviors fire.

Runs a real PetWindow offscreen, leaves it alone for 135 s, and logs
every animation transition (blink / scratch / sleep).
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from app.pet_window import PetWindow

app = QApplication(sys.argv)
win = PetWindow(sfx=None)
win.show()

events = []


def tick():
    name = win.player.name
    idx = getattr(win.player, "index", None)
    events.append((round(app_elapsed(), 1), name, idx))


t0 = None


def app_elapsed():
    from PySide6.QtCore import QElapsedTimer
    return t0.elapsed() / 1000.0


from PySide6.QtCore import QElapsedTimer

t0 = QElapsedTimer()
t0.start()

sampler = QTimer()
sampler.timeout.connect(tick)
sampler.start(250)

QTimer.singleShot(135000, app.quit)
app.exec()

# compress to transitions
prev = None
for t, name, idx in events:
    key = (name, idx if name in ("tap3", "drag") else None)
    if key != prev:
        print(f"t={t:6.1f}s  anim={name} idx={idx}")
        prev = key
print("audit done")
