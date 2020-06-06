#!/usr/bin/env python3

# Copyright (C) 2018 by Akkana Peck.
# Share and enjoy under the GPL v2 or later.

"""Viewer for HTML presentations."""


import sys
import os
import argparse

from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QShortcut, QDesktopWidget, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage


class PresoView(QWebEngineView):

    def __init__(self, url=None, curviews=None, fullscreen=False, monitor=-1,
                 zoom=1.0, show_notes=True):
        """Create a new PresoView. Leave curviews unset unless requesting
           a new window, in which case it must be set to a list of
           existing PresoViews.
           Monitor is the monitor number from xrandr.
        """
        # Example showing list of views (the ONLY one I've found):
        # https://stackoverflow.com/questions/55472415/python-pyqt5-window-does-not-open-new-window-or-tab-on-external-url-link-click

        super().__init__()

        self._windows = [] if not curviews else curviews
        self._windows.append(self)

        # Are we making screenshots? TODO: make this a command-line param.
        self.make_screenshots = False
        self.imgnum = 0

        # Size the audience will see (used for converting to images):
        displaysize = QDesktopWidget().screenGeometry(-1)
        self.displaywidth = displaysize.width()
        self.displayheight = displaysize.height()

        # Size of the window we'll actually display.
        # XXX Currently assumes a projector at 1024x768
        # and should be made more general.
        self.fullwidth = 1366 if show_notes else 1024
        self.fullheight = 768

        if zoom != 1.0 :
            self.displaywidth = int(self.displaywidth * zoom)
            self.displayheight = int(self.displayheight * zoom)
            self.fullwidth = int(self.fullwidth * zoom)
            self.fullheight = int(self.fullheight * zoom)
            print("Display size: %d x %d" % (self.displaywidth,
                                             self.displayheight))
            print("Full size: %d x %d" % (self.fullwidth,
                                          self.fullheight))

        if monitor >= 0:
            # The number of the monitor where the window should show up
            screens = app.screens()
            print("screens:", screens)
            if monitor > len(screens):
                print("There is no monitor", monitor)
                sys.exit(1)

            geom = screens[monitor].geometry()
            self.move(geom.left(), geom.top())
            self.showFullScreen()

        else:
            # Run fullscreen if the display is XGA or smaller,
            # or if fullscreen was explicitly set.
            # displaysize = QApplication.desktop.screenGeometry()
            if fullscreen or self.displayheight <= 768:
                self.showFullScreen()

        # Key bindings
        # For keys like function keys, use QtGui.QKeySequence("F12")
        QShortcut("Ctrl+Q", self, activated=self.close)
        QShortcut("Ctrl+R", self, activated=self.reload)

        QShortcut("Alt+Left", self, activated=self.back)
        QShortcut("Alt+Right", self, activated=self.forward)

        self.resize(self.fullwidth, self.fullheight)
        if url:
            self.load(QUrl.fromUserInput(url))


    def createWindow(self, wintype):
        """Create an empty window when requested to do so by
           Javascript or _target.
           JS may pass a size, and either JS or target will likely pass
           a URL, but does QWebEngineView pass that info along? Nooooo!
           I don't know if there's any way to get those details.
           Even qutebrowser just punts on new window creation.
        """
        # Possible wintypes (all part of QWebEnginePage):
        # WebBrowserWindow:        A new window
        # WebBrowserTab:           A new tab
        # WebDialog:               A JavaScript-created window
        # WebBrowserBackgroundTab: A new tab that isn't immediately active

        if wintype in [QWebEnginePage.WebBrowserWindow, QWebEnginePage.WebDialog]:
            v = PresoView('about:blank', curviews=self._windows)
            # v.resize(640, 480)
            v.show()
            return v

    # def resizeEvent(self, e):
    #     """This is called on window create, but not from javascript resizeTo.

    #     Args:
    #         e: The QResizeEvent
    #     """
    #     print("resizeEvent!", e)
    #     print("Current geometry", self.geometry())
    #     print("new size", e.size())
    #     print("old size", e.oldSize())
    #     super().resizeEvent(e)
    #     # self._update_overlay_geometries()
    #     # self._downloadview.updateGeometry()
    #     # self.tabbed_browser.widget.tabBar().refresh()


    # def event(self, ev):
    #     print("event!", ev)
    #     return super().event(ev)


def parse_args():
    """Parse commandline arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--fullscreen", dest="fullscreen", default=False,
                        action="store_true",
                        help="Run fullscreen regardless of screen size")
    parser.add_argument('-m', '--monitor', action="store", default=-1,
                        dest="monitor", type=int,
                        help='Run fullscreen on this monitor')
    parser.add_argument('url', help='The URL to open')

    args = parser.parse_known_args()[0]

    # Figure out if the url is a filename or a url
    if args.url.find(':') < 0 :
        if args.url[0] == '/' :
            args.url = 'file://' + args.url
        else :
            args.url = 'file://' + os.getcwd() + '/' + args.url

    return args


if __name__ == '__main__':

    # Try to catch exceptions instead of dumping core,
    # but it dumps core anyway.
    import traceback
    def excepthook(excType=None, excValue=None, tracebackobj=None, *,
                   message=None, version_tag=None, parent=None):
        # print("exception! excValue='%s'" % excValue)
        # logging.critical(''.join(traceback.format_tb(tracebackobj)))
        # logging.critical('{0}: {1}'.format(excType, excValue))
        traceback.print_exception(excType, excValue, tracebackobj)
    sys.excepthook = excepthook

    args = parse_args()

    app = QApplication(sys.argv)

    pv = PresoView(args.url, fullscreen=args.fullscreen, monitor=args.monitor)
    pv.show()

    app.exec_()
