#!/usr/bin/env python3

# https://stackoverflow.com/questions/68594746/pyqt5-transparent-background-but-also-interactable

import sys

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow

# from PIL import Image

# This overrides Qt's silly trapping of Ctrl-C,
# so you don't have to Ctrl-\ and get a core dump every time.
from PyQt5 import QtCore, QtGui, QtWidgets
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


class TransWin(QMainWindow):

    def __init__(self, imgfile, position, opacity):
        super().__init__()

        self.imgfile = imgfile
        self.x0, self.y0 = position
        self.opacity = opacity/100

        self.drawing = False
        self.lastPoint = QPoint()

        self.initUI()

    def initUI(self):
        # self.setStyleSheet("background: transparent;")
        # self.background.fill(Qt.transparent)
        self.background = QPixmap(self.imgfile)
        width = self.background.width()
        height = self.background.height()
        self.setGeometry(self.x0, self.y0, width, height)
        # self.resize(new_width, new_height))

        # Translucent background
        self.setWindowOpacity(self.opacity)
        # self.setAttribute(Qt.WA_TranslucentBackground)

        # Make mouse events click through:
        # https://stackoverflow.com/a/70438754
        self.setWindowFlags(self.windowFlags()
                            # This is necessary but not sufficient:
                            # apparently it's mainly for passing events
                            # through to lower windows *from the same app*:
                            | Qt.WindowTransparentForInput

                            # This is the key: with X11BypassWindowManagerHint
                            # I can click through the window -- but
                            # it has no titlebar and I can't move it,
                            # so it's stuck at the upper left corner
                            # of the screen. Also since it can't get
                            # key events either, the only way to exit
                            # is to SIGQUIT and take the core dump.
                            | Qt.X11BypassWindowManagerHint
                            )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.background)

    def keyPressEvent(self, e):
        print("keypress")
        if e.text() == 'q':
            QApplication.quit()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Show an image transparently, with click-through")
    parser.add_argument('imgfile', help='Image to show')
    parser.add_argument('-p', '--position', nargs=2, type=int,
                        default=[300, 300], help="Window position")
    parser.add_argument('-o', '--opacity', type=int, default=50,
                        help='opacity (percent: default 50)')
    args = parser.parse_args(sys.argv[1:])

    app = QApplication(sys.argv)
    window = TransWin(args.imgfile,
                      position=args.position, opacity=args.opacity)
    window.show()
    sys.exit(app.exec_())

