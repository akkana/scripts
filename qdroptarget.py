#!/usr/bin/env python3

"""
A PyQt6 drop target. Also understands middleclick paste.

Optionally, you can specify a command to run whenever something
is dropped or pasted into the window.

Derived from the ZetCode PyQt6 tutorial by Jan Bodnar
Copyright 2023 by Akkana Peck: share and enjoy under the GPLv2 or later.
"""

import sys, os

import subprocess

from PyQt6.QtWidgets import (QPushButton, QWidget, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QClipboard, QKeySequence, QShortcut


class DropButton(QPushButton):

    def __init__(self, parent, command=None):

        self.title = "Drop\nURL\nhere"
        self.command = command

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
        text = e.mimeData().text()
        self.invert()
        self.timer.start()
        if self.command:
            self.run_command(text)
        else:
            print("Dropped:", text)

    def mouseReleaseEvent(self, e):
        """On middleclick release, get the PRIMARY selection if possible,
           else CLIPBOARD.
        """
        if e.button() != Qt.MouseButton.MiddleButton:
            return

        # Pyside docs (which seem to be all that exist, I haven't
        # found any pyqt6 docs on QClipboard) say you can do
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

        text = QApplication.clipboard().text(mode=mode)
        if self.command:
            self.run_command(text)
        else:
            print("Pasted:", text)

    def run_command(self, text):
        if not self.command:
            print("qdroptarget:", command)
            return
        command = self.command.replace('%s', text)
        subprocess.run(["sh", "-c", command])

    def invert(self):
        if self.inverted:
            self.setStyleSheet("background-color: white")
            self.setText(self.title)
        else:
            self.setStyleSheet("background-color: black; color: white")
            self.setText("Dropped")
        self.inverted = not self.inverted


class DropWindow(QWidget):

    def __init__(self, command=None):
        super().__init__()

        button = DropButton(self, command=command)

        self.shortcut_quit = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_quit.activated.connect(lambda : sys.exit())

        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)


def Usage():
    print(f"""Usage: {os.path.basename(sys.argv[0])} [command]

If a command is provided (quoted), it will be run any time something is
dropped onto or middlemouse-pasted into the window, with any occurrences
of %s in the command replaced with the text dropped/pasted.
For instance, you could use a command like 'sensible-browser %s'.
Obviously, don't let people you don't trust drag into this window.""")
    sys.exit(1)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '-h' or sys.argv[1] == '--help':
            Usage()
        command = sys.argv[-1]
        if '%s' not in command:
            Usage()
    else:
        command = None

    rc = os.fork()
    if rc:
        sys.exit(0)

    app = QApplication(sys.argv)
    win = DropWindow(command=command)
    win.show()
    app.exec()


if __name__ == '__main__':
    main()
