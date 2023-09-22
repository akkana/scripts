#!/usr/bin/env python3

"""
A PyQt6 drop target. Also understands middleclick paste.

Derived from the ZetCode PyQt6 tutorial by Jan Bodnar
Copyright 2023 by Akkana Peck: share and enjoy under the GPLv2 or later.
"""

import sys

from PyQt6.QtWidgets import (QPushButton, QWidget, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt5.QtGui import QClipboard


class DropButton(QPushButton):

    def __init__(self, parent):

        self.title = "Drop\nURL\nhere"

        super().__init__(self.title, parent)

        self.setAcceptDrops(True)
        self.resize(100, 70)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.invert)

        self.inverted = False

    def dragEnterEvent(self, e):
        mime_data = e.mimeData()
        # print("Formats:", mime_data.formats())
        if mime_data.hasFormat('text/plain'):
            e.accept()
            self.setStyleSheet("background-color: green; color: white")
        else:
            print("Ignoring, no text/plain")
            e.ignore()

    def dropEvent(self, e):
        print("Dropped:", e.mimeData().text())
        self.invert()
        self.timer.start()

    def mouseReleaseEvent(self, e):
        """On middleclick release, get the PRIMARY selection if possible,
           else CLIPBOARD.
        """
        if e.button() != Qt.MouseButton.MiddleButton:
            print("Ignoring button", e.button())
            return

        # Pyside docs (which seem to be all that exist, I haven't found
        # any pyqt6 docs on QClipboard) say you can do
        # QClipboard().supportsSelection() and
        # mode=QClipboard.Mode.Selection,
        # but in reality those lead to core dumps with
        # "argument 'mode' has unexpected type 'Mode'" and
        # "'mode' is not a valid keyword argument".
        # Instead, use QApplication.clipboard().Mode.Selection.
        if QApplication.clipboard().supportsSelection():
            mode = QApplication.clipboard().Mode.Selection
        else:
            print("No Selection (PRIMARY) support! Using clipboard instead")
            mode = QApplication.clipboard().Mode.Clipboard

        selection_text = QApplication.clipboard().text(mode=mode)
        print("Pasted:", selection_text)

    def invert(self):
        if self.inverted:
            self.setStyleSheet("background-color: white")
            self.setText(self.title)
        else:
            self.setStyleSheet("background-color: black; color: white")
            self.setText("Dropped")
        self.inverted = not self.inverted


class DropWindow(QWidget):

    def __init__(self):
        super().__init__()

        button = DropButton(self)


def main():
    app = QApplication(sys.argv)
    win = DropWindow()
    win.show()
    app.exec()


if __name__ == '__main__':
    main()
