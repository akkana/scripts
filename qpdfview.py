#!/usr/bin/env python3

# How to view PDF in a Qt5 widget.
# Poppler has almost no documentation and Python-Qt5 isn't much better,
# so maybe this will help someone.
# Copyright 2018 by Akkana Peck: share and enjoy under the GPLv2 or later.

# Uses popplerqt5: https://pypi.org/project/python-poppler-qt5/
# or Debian package python3-poppler-qt5

# Poppler is theoretically available from gi (instead of popplerqt5),
# but I haven't found any way to get that Poppler to work.
# import gi
# gi.require_version('Poppler', '0.18')
# from gi.repository import Poppler

import sys
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QPoint, QSize

from popplerqt5 import Poppler

# Poppler gives page sizes in points, so 72 DPI.
# If you want to use a DPI other than 72, you have to convert.
POINTS_PER_INCH = 72

class PDFWidget(QWidget):

    def __init__(self, filename, dpi=72):
        super().__init__()

        self.filename = filename

        # Using Poppler from gi.repository:
        # (This part works, it's the part in paint() that doesn't.)
        # self.document = Poppler.Document.new_from_file('file://' + filename,
        #                                                None)
        # self.page = self.document.get_page(0)

        # Using Poppler from popplerqt5:
        self.document = Poppler.Document.load(filename)
        # self.document.setRenderHint(Poppler.Document.TextHinting)
        self.document.setRenderHint(Poppler.Document.TextAntialiasing)
        self.page = self.document.page(0)
        self.dpi = dpi

        pagesize = self.page.pageSize()

        # self.setGeometry(0, 0,
        #                  pagesize.width() * self.dpi/POINTS_PER_INCH,
        #                  pagesize.height() * self.dpi/POINTS_PER_INCH)
        # self.setSizePolicy(
        # self.sizeHint = QSize(
        self.resize(pagesize.width() * self.dpi/POINTS_PER_INCH,
                    pagesize.height() * self.dpi/POINTS_PER_INCH)

        self.setWindowTitle('PDF Viewer')
        self.show()


    def paintEvent(self, event):

        # Poppler from gi.repository:
        # self.page.render(SOME_CAIRO_SURFACE)

        # Poppler from popplerqt5:
        qp = QPainter()
        qp.begin(self)
        # Not clear how to use renderToPainter(): not like this, apparently.
        # self.page.renderToPainter(qp)

        img = self.page.renderToImage(self.dpi, self.dpi)
        qp.drawImage(QPoint(0, 0), img)
        qp.end()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = PDFWidget(sys.argv[1])
    sys.exit(app.exec_())

