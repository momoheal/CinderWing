"""Verify the full event-flow simulation with the real PetWindow + Bubble."""
import sys

from PySide6.QtWidgets import QApplication

from app.bubble import Bubble
from app.dev_sim import simulate
from app.pet_window import PetWindow
from app.sfx import Sfx

SHOT_DIR = (
    r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default"
    r"\.doubaowork\agent_mode\workspace\.sessions\38444948096752642"
    r"\agents\m_0cwpwYn3kVx"
)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    sfx = Sfx()
    win = PetWindow(sfx)
    bubble = Bubble(win)
    win.bubble = bubble
    win.move(1467, 775)
    win.show()
    simulate(win)

    marks = [(600, "flow_start.png"), (4600, "flow_progress.png"),
             (8600, "flow_waiting.png"), (16700, "flow_done.png")]

    def shoot(name):
        import subprocess
        subprocess.run(
            [r"C:\git-repo\pet\.venv\Scripts\python.exe",
             r"C:\git-repo\pet\tools\screen_shot.py",
             rf"{SHOT_DIR}\{name}",
             "4900", "900", "640", "720"],
            check=False,
        )

    for ms, name in marks:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(ms, lambda n=name: shoot(n))
    from PySide6.QtCore import QTimer
    QTimer.singleShot(18000, app.quit)
    app.exec()


if __name__ == "__main__":
    main()
