#!/usr/bin/env python3

# How to view PDF in a Qt5 widget.
# Poppler has almost no documentation and Python-Qt5 isn't much better,
# so maybe this will help someone.
# Copyright 2018 by Akkana Peck: share and enjoy under the GPLv2 or later.

# Uses popplerqt5: https://pypi.org/project/python-poppler-qt5/
# or Debian package python3-poppler-qt5

# Poppler is theoretically available from gi (instead of popplerqt5),
# but I haven't found any way to get that Poppler to work with Qt5
# because it can only draw to a Cairo context.
# import gi
# gi.require_version('Poppler', '0.18')
# from gi.repository import Poppler

import sys
import traceback

from PyQt5.QtWidgets import QWidget, QApplication, QShortcut, \
     QLabel, QScrollArea, QSizePolicy, QVBoxLayout
from PyQt5.QtGui import QPainter, QColor, QFont, QPixmap
from PyQt5.QtCore import Qt, QPoint, QSize, QUrl, QByteArray
from PyQt5.QtNetwork import QNetworkAccessManager, \
     QNetworkReply, QNetworkRequest

from popplerqt5 import Poppler

# Poppler gives page sizes in points, so 72 DPI.
# If you want to use a DPI other than 72, you have to convert,
# and initial page sizes are given in pixels assuming 72 DPI.
POINTS_PER_INCH = 72

class PDFWidget(QLabel):

    '''
    A widget showing one page of a PDF.
    If you want to show multiple pages of the same PDF,
    make sure you share the document (let the first PDFWidget
    create the document, then pass thatPDFwidget.document to any
    subsequent widgets you create) or use a ScrolledPDFWidget.
    Will try to resize to a reasonable size to fit inside the
    geometry passed in (typically the screen size, a PyQt5.QtCore.QRect);
    or specify dpi explicitly.
    '''

    def __init__(self, url, document=None, pageno=1, dpi=None,
                 geometry=None, parent=None, load_cb=None):
        '''
           load_cb: will be called when the document is loaded.
        '''
        super(PDFWidget, self).__init__(parent)

        self.geometry = geometry

        # Guess at initial size: will be overridden later.
        if geometry:
            self.winwidth = geometry.height() * .75
            self.winheight = geometry.height()
        else:
            self.geometry = PyQt5.QtCore.QSize(600, 800)
            self.winwidth = 600
            self.winheight = 800

        self.filename = url

        self.load_cb = load_cb

        self.network_manager = None

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        if not document:
            self.document = None
            if url:
                self.start_load(url)
        else:
            self.document = document
        self.page = None
        self.pagesize = QSize(self.winwidth, self.winheight)

        self.dpi = dpi

        # Poppler page numbering starts from 0 but that's not what
        # most PDF users will expect, so subtract:
        if pageno > 0:
            pageno -= 1
        self.pageno = pageno

        self.render()

    def sizeHint(self):
        if not self.page:
            if not self.document:
                return QSize(self.winwidth, self.winheight)
            self.page = self.document.page(self.pageno)

        if not self.pagesize:
            self.pagesize = self.page.pageSize()

        return self.pagesize

    def render(self):
        '''Render to a pixmap at the current DPI setting.
        '''
        if not self.document:
            return

        if not self.page:
            self.page = self.document.page(self.pageno)
            self.pagesize = self.page.pageSize()

            self.document.setRenderHint(Poppler.Document.TextAntialiasing)
            # self.document.setRenderHint(Poppler.Document.TextHinting)

        if not self.dpi:
            # Probably first time here.
            # self.pagesize is sized in pixels assuming POINTS_PER_INCH;
            # adjust that so the page barely fits on in self.geometry.

            # First assume that it's portrait aspect ratio and that
            # vertical size will be the limiting factor.
            self.dpi = POINTS_PER_INCH * \
                self.geometry.height() / self.pagesize.height()

            # Was that too much: will it overflow in width?
            if self.pagesize.width() * self.dpi / POINTS_PER_INCH \
               > self.geometry.width():
                self.dpi = POINTS_PER_INCH * \
                    self.geometry.width() / self.pagesize.width()

            self.winwidth = self.pagesize.width() * self.dpi / POINTS_PER_INCH
            self.winheight = self.pagesize.height() * self.dpi / POINTS_PER_INCH

            # Most Qt5 programs seem to use setGeometry(x, y, w, h)
            # to set initial window size. resize() is the only method I've
            # found that doesn't force initial position as well as size.
            self.resize(self.winwidth, self.winheight)

        self.setWindowTitle('PDF Viewer')

        img = self.page.renderToImage(self.dpi, self.dpi)
        self.pixmap = QPixmap.fromImage(img)
        self.setPixmap(self.pixmap)

    def start_load(self, url):
        '''Create a Poppler.Document from the given URL, QUrl or filename.
           Return, then asynchronously call self.load_cb.
        '''

        # If it's not a local file, we'll need to load it.
        # http://doc.qt.io/qt-5/qnetworkaccessmanager.html
        qurl = QUrl(url)
        if not qurl.scheme():
            qurl = QUrl.fromLocalFile(url)
        if not self.network_manager:
            self.network_manager = QNetworkAccessManager();
        self.network_manager.finished.connect(self.download_finished)
        self.network_manager.get(QNetworkRequest(qurl))

    def download_finished(self, network_reply):
        qbytes = network_reply.readAll()
        self.document = Poppler.Document.loadFromData(qbytes)

        self.render()

        if self.load_cb:
            self.load_cb()


class PDFScrolledWidget(QScrollArea):

    '''
    Show all pages of a PDF, with scrollbars.
    '''

    def __init__(self, filename, dpi=72, geometry=None, parent=None):
        super(PDFScrolledWidget, self).__init__(parent)

        self.loaded = False

        self.vscrollbar = None

        self.setWidgetResizable(True)

        self.geometry = geometry

        # Try to eliminate the guesswork in sizing the window to content:
        self.setFrameShape(self.NoFrame)

        # I would like to set both scrollbars to AsNeeded:
        # but if the vertical scrollbar is AsNeeded, the content
        # gets loaded initially, then the QScrollArea decides it
        # needs a vertical scrollbar, adds it and resizes the content
        # inside, so everything gets scaled by 0.98.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Create a widget inside the scroller for the VBox layout to use:
        self.scroll_content = QWidget()
        self.setWidget(self.scroll_content)

        # A VBox to lay out all the pages vertically:
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Create the widget for the first page of the PDF,
        # which will also create the Poppler document we'll use
        # to render the other pages.
        self.pages = [ PDFWidget(filename, document=None, pageno=1,
                                 geometry=self.geometry,
                                 load_cb = self.load_cb) ]
        self.pages[0].setContentsMargins(0, 0, 0, 0)
        self.pages[0].setFrameShape(self.NoFrame)

        # Add page 1 to the vertical layout:
        self.scroll_layout.addWidget(self.pages[0])

        QShortcut("Space", self, activated=self.page_down)
        QShortcut("Shift+Space", self, activated=self.page_up)


    def load_cb(self):
        page1 = self.pages[0]

        width = page1.width()
        height = page1.height()
        if self.vscrollbar:
            sbw = self.vscrollbar.width()
            width += sbw
            height += sbw

        for p in range(2, page1.document.numPages()):
            pagew = PDFWidget(page1.filename, document=page1.document,
                              geometry=self.geometry,
                              pageno=p, dpi=page1.dpi)
            pagew.setContentsMargins(0, 0, 0, 0)

            # pagew.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            self.scroll_layout.addWidget(pagew)
            self.pages.append(pagew)

        self.scroll_layout.addStretch(1)

        # Now there's a size. Set the initial page size to be big enough
        # to show one page, including room for scrollbars, at 72 DPI.
        self.resize_to_fit_content()

        # Don't set the loaded flag until after the first set of resizes,
        # so resizeEvent() won't zoom.
        self.loaded = True


    def resize_to_fit_content(self):
        '''Resize to be wide enough not to show a horizontal scrollbar,
           and just a little taller than the first page of PDF content.
        '''
        if not self.vscrollbar:
            self.vscrollbar = self.verticalScrollBar()
        if self.vscrollbar:
            vscrollbarwidth = self.vscrollbar.width()
        else:
            vscrollbarwidth = 14

        # Getting the size of a widget is tricky.
        # self.widget().width(), for some reason, gives the width minus 12
        # pixels, while self.widget().sizeHint().width() gives the
        # correct size.
        # So that means, apparently, if you want the margins of a widget
        # you can get them by subtracting width() and height() from sizeHint().
        # print("widget width is", self.widget().width(),
        #       ", sizehint", self.widget().sizeHint().width())
        width = self.widget().sizeHint().width() + vscrollbarwidth
        height = self.widget().sizeHint().height()
        self.resize(width, height)


    def page_down(self):
        vbar = self.verticalScrollBar()
        vbar.setValue(vbar.value() + vbar.pageStep())


    def page_up(self):
        vbar = self.verticalScrollBar()
        vbar.setValue(vbar.value() - vbar.pageStep())


    def resizeEvent(self, event):
        '''On resizes after the initial resize,
           re-render the PDF to fit the new width.
        '''
        oldWidth = event.oldSize().width()
        newWidth = event.size().width()

        if oldWidth > 0 and self.loaded:
            self.zoom(newWidth / oldWidth)

        super(PDFScrolledWidget, self).resizeEvent(event)


    def zoom(self, frac=1.25):
        '''Zoom the page by the indicated fraction.
        '''
        for page in self.pages:
            # Resize according to width, ignoring height.
            page.dpi *= frac
            page.render()


    def unzoom(self, frac=.8):
        '''Zoom the page by the indicated fraction.
           Same as unzoom but with a default that zooms out instead of in.
        '''
        self.zoom(frac)


if __name__ == '__main__':
    #
    # PyQt is super crashy. Any little error, like an extra argument in a slot,
    # causes it to kill Python with a core dump.
    # Setting sys.excepthook works around this , and execution continues.
    #
    def excepthook(excType=None, excValue=None, tracebackobj=None, *,
                   message=None, version_tag=None, parent=None):
        # print("exception! excValue='%s'" % excValue)
        # logging.critical(''.join(traceback.format_tb(tracebackobj)))
        # logging.critical('{0}: {1}'.format(excType, excValue))
        traceback.print_exception(excType, excValue, tracebackobj)

    sys.excepthook = excepthook

    app = QApplication(sys.argv)

    # It's helpful to know screen size, to choose appropriate DPI.
    # XXX It's currently ignored but will eventually be used.
    desktops = QApplication.desktop()
    geometry = desktops.screenGeometry(desktops.screenNumber())
    # print("screen geometry is", geometry.width(), geometry.height())

    # w = PDFWidget(sys.argv[1], geometry=geometry)
    w = PDFScrolledWidget(sys.argv[1], geometry=geometry)

    QShortcut("Ctrl+Q", w, activated=w.close)

    w.show()

    sys.exit(app.exec_())

