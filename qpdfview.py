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
from PyQt5.QtGui import QPainter, QColor, QFont, QPixmap
from PyQt5.QtCore import Qt, QPoint, QSize

from popplerqt5 import Poppler

# Poppler gives page sizes in points, so 72 DPI.
# If you want to use a DPI other than 72, you have to convert.
POINTS_PER_INCH = 72

class PDFWidget(QLabel):

    '''
    A widget showing one page of a PDF.
    If you want to show multiple pages of the same PDF,
    make sure you share the document (let the first PDFWidget
    create the document, then pass thatPDFwidget.document to any
    subsequent widgets you create) or use a ScrolledPDFWidget.
    '''

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

        self.pagesize = self.page.pageSize()

        self.render()

    def render(self):
        '''Render to a pixmap at the current DPI setting.
        '''
        # Most Qt5 programs seem to use setGeometry(x, y, w, h)
        # to set initial window size. resize() is the only method I've
        # found that doesn't force initial position as well as size.
        self.resize(self.pagesize.width() * self.dpi/POINTS_PER_INCH,
                    self.pagesize.height() * self.dpi/POINTS_PER_INCH)

        self.setWindowTitle('PDF Viewer')

        img = self.page.renderToImage(self.dpi, self.dpi)
        self.pixmap = QPixmap.fromImage(img)
        self.setPixmap(self.pixmap)

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


class PDFScrolledWidget(QScrollArea):   # inherit from QScrollArea?

    '''
    Show all pages of a PDF, with scrollbars.
    '''

    def __init__(self, filename, dpi=72):
        super(PDFScrolledWidget, self).__init__()

        self.setWidgetResizable(True)

        scroll_contents = QWidget()
        self.setWidget(scroll_contents)

        self.scroll_layout = QVBoxLayout(scroll_contents)

        self.pages = [ PDFWidget(filename, document=None, pageno=1, dpi=dpi) ]
        self.scroll_layout.addWidget(self.pages[0])

        scrollbar_size = 5    # pixels
        self.resize(self.pages[0].width() + scrollbar_size,
                    self.pages[0].height() + scrollbar_size)

        for p in range(2, self.pages[0].document.numPages()):
            document = None
            pagew = PDFWidget(filename, document=document, pageno=p, dpi=dpi)
            # pagew.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            self.scroll_layout.addWidget(pagew)
            self.pages.append(pagew)

        self.scroll_layout.addStretch(1)

        self.show()

    def resizeEvent(self, event):
        oldWidth = event.oldSize().width()
        newWidth = event.size().width()

        if oldWidth > 0:
            self.zoom(newWidth / oldWidth)

        super(PDFScrolledWidget, self).resizeEvent(event)

    def zoom(self, frac=1.25):
        for page in self.pages:
            # Resize according to width, ignoring height.
            page.dpi *= frac
            page.render()

    def unzoom(self, frac=.8):
        self.zoom(frac)


if __name__ == '__main__':

    app = QApplication(sys.argv)

    w = PDFScrolledWidget(sys.argv[1])
    # w = PDFWidget(sys.argv[1])
    w.show()

    sys.exit(app.exec_())

