"""Harness: real app + full event-flow simulation, stays running for capture."""
import sys

from PySide6.QtWidgets import QApplication

from app.bubble import Bubble
from app.dev_sim import simulate
from app.pet_window import PetWindow
from app.sfx import Sfx


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    sfx = Sfx()
    win = PetWindow(sfx)
    win.bubble = Bubble(win)
    win.move(1467, 775)
    win.show()
    simulate(win)
    app.exec()


if __name__ == "__main__":
    main()
