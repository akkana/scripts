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
from PyQt5.QtWidgets import QWidget, QApplication, \
     QLabel, QScrollArea, QSizePolicy, QVBoxLayout
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QPoint, QSize

from popplerqt5 import Poppler

# Poppler gives page sizes in points, so 72 DPI.
# If you want to use a DPI other than 72, you have to convert.
POINTS_PER_INCH = 72

class PDFWidget(QWidget):    # Or inherit from QLabel?

    def __init__(self, filename, document=None, pageno=1, dpi=72):
        super(PDFWidget, self).__init__()

        self.filename = filename

        if not document:
            self.document = PDFWidget.new_document(filename)
        else:
            self.document = document

        self.dpi = dpi

        # Poppler page numbering starts from 0 but that's not what
        # most PDF users will expect, so subtract:
        if pageno > 0:
            pageno -= 1
        self.page = self.document.page(pageno)

        pagesize = self.page.pageSize()

        # Most Qt5 programs seem to use setGeometry(x, y, w, h)
        # to set initial window size. resize() is the only method I've
        # found that doesn't force initial position as well as size.
        self.resize(pagesize.width() * self.dpi/POINTS_PER_INCH,
                    pagesize.height() * self.dpi/POINTS_PER_INCH)

        self.setWindowTitle('PDF Viewer')

        self.show()

    #classmethod
    def new_document(filename):
        '''Create a Poppler.Document from the given URL or filename.
        '''

        # Using Poppler from gi.repository:
        # (This part works, it's the part in paint() that doesn't.)
        # self.document = Poppler.Document.new_from_file('file://' + filename,
        #                                                None)
        # self.page = self.document.get_page(0)

        # Using Poppler from popplerqt5:
        document = Poppler.Document.load(filename)
        # self.document.setRenderHint(Poppler.Document.TextHinting)
        document.setRenderHint(Poppler.Document.TextAntialiasing)

        return document


        '''pages can be either a number (1), a list ([1, 2, 3])
           or a string ("*", "all", "1-5").
           At least eventually.
        '''

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

class PDFScrolledWidget(QScrollArea):

    def __init__(self, filename, dpi=72):
        super(PDFScrolledWidget, self).__init__()

        self.pdfw = PDFWidget(filename, document=None, pageno=1, dpi=dpi)
        self.pdfw.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        # self.pdfw.setScaledContents(True)

        # # self.imageLabel.setBackgroundRole(QPalette.Base)
        # self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        # self.setScaledContents(True)

        # self.scrollArea = QScrollArea()
        # # self.scrollArea.setBackgroundRole(QPalette.Dark)
        # self.scrollArea.setWidget(self.imageLabel)
        # self.setCentralWidget(self.scrollArea)

        # self.scrollArea.setBackgroundRole(QPalette.Dark)

        vbox = QVBoxLayout()
        vbox.addWidget(self.pdfw)
        self.setLayout(vbox)

        self.setWidget(self.pdfw)

        scrollbar_size = 5    # pixels
        self.resize(self.pdfw.width() + scrollbar_size,
                    self.pdfw.height() + scrollbar_size)

        self.show()

if __name__ == '__main__':

    app = QApplication(sys.argv)

    w = PDFScrolledWidget(sys.argv[1])
    # w = PDFWidget(sys.argv[1])

    sys.exit(app.exec_())

