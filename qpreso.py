#!/usr/bin/env python3

# Copyright (C) 2018 by Akkana Peck.
# Share and enjoy under the GPL v2 or later.

"""Viewer for HTML presentations."""


# XXX This saves a bunch of stuff in ~/.local/share/qpreso,
# should try to avoid that.


import sys
import os
import argparse

from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QShortcut, QDesktopWidget, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

class PresoView(QWebEngineView):

    def __init__(self, url=None, curviews=None, fullscreen=False, monitor=-1,
                 resolution=None, zoom=1.0, show_notes=True):
        """Create a new PresoView. Leave curviews unset unless requesting
           a new window, in which case it must be set to a list of
           existing PresoViews.
           Monitor is the monitor number from xrandr.
        """
        # Example showing list of views (the ONLY one I've found):
        # https://stackoverflow.com/questions/55472415/python-pyqt5-window-does-not-open-new-window-or-tab-on-external-url-link-click

        super().__init__()

        if not curviews:
            self._windows = []
        else:
            self._windows = curviews
        self._windows.append(self)

        # Are we making screenshots? TODO: make this a command-line param.
        self.make_screenshots = False
        self.imgnum = 0

        # Size the audience will see (used for converting to images):
        # Doesn't work, returns the geometry of monitor 0 no matter what.
        # displaysize = QDesktopWidget().screenGeometry(-1)

        # Get the screen geometry and set size and position appropriately.
        screens = app.screens()

        # monitor is the # of the monitor where the window should show up.
        if monitor >= len(screens):
            print("There is no monitor", monitor)
            sys.exit(1)
        if monitor < 0:
            # If no monitor is specified, force 0. Otherwise qt will
            # get it wrong, and will use the geometry of screen 0 even
            # if the window manager puts the app on screen 1.
            monitor = 0

        geom = screens[monitor].geometry()

        if resolution:
            parts = resolution.split('x')
            self.displaywidth = int(parts[0])
            if len(parts) > 1:
                self.displayheight = int(parts[1])
            elif show_notes:
                self.displayheight = int(self.displaywidth * 768/1366)
            else:
                self.displayheight = int(self.displaywidth * 3 / 4)

            self.fullwidth = self.displaywidth
            self.fullheight = self.displayheight

            # print("Resolution", self.displaywidth, self.displayheight)

        else:
            self.displaywidth = geom.width()
            self.displayheight = geom.height()

            # Fullscreen only in the main window, not popups which will have
            # an about:blank URL.
            if url and url != 'about:blank':
                self.move(geom.left(), geom.top())
                if (fullscreen or self.displayheight <= 768):
                    # Run fullscreen if the display is XGA or smaller
                    # and it isn't a dialog window,
                    # or if fullscreen was explicitly set.
                    # displaysize = QApplication.desktop.screenGeometry()
                    self.showFullScreen()

            # Size of the window we'll actually display.
            # XXX Currently assumes a projector at 1024x768
            # and should be made more general.
            if show_notes:
                self.fullwidth = 1366
            else:
                self.fullwidth = 1024
            self.fullheight = 768

        if zoom != 1.0 :
            self.displaywidth = int(self.displaywidth * zoom)
            self.displayheight = int(self.displayheight * zoom)
            self.fullwidth = int(self.fullwidth * zoom)
            self.fullheight = int(self.fullheight * zoom)
            # print("Display size: %d x %d" % (self.displaywidth,
            #                                  self.displayheight))
            # print("Full size: %d x %d" % (self.fullwidth,
            #                               self.fullheight))

        # Key bindings
        # For keys like function keys, use QtGui.QKeySequence("F12")
        QShortcut("Ctrl+Q", self, activated=self.exit)
        QShortcut("Ctrl+R", self, activated=self.reload)

        QShortcut("Alt+Left", self, activated=self.back)
        QShortcut("Alt+Right", self, activated=self.forward)

        self.resize(self.fullwidth, self.fullheight)
        if url:
            self.load(QUrl.fromUserInput(url))

    def exit(self):
        app.closeAllWindows()

    # Attempt 1 at getting JS console.log messages (doesn't work):
    def javaScriptConsoleMessage(self, level, msg, line, sourceID):
        print(level, msg, line, sourceID)


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

        if wintype == QWebEnginePage.WebBrowserWindow or \
           wintype == QWebEnginePage.WebDialog:
            v = PresoView('about:blank', curviews=self._windows)
            # v.resize(640, 480)
            v.show()
            return v


def parse_args():
    """Parse commandline arguments."""
    parser = argparse.ArgumentParser(
description="""Lightweight tool for displaying HTML presentations.

Tip: For debugging, run with --remote-debugging-port=[portnum]
     and then you can get debug tools with chromium to localhost:[portnum]
     (doesn't seem to work with Firefox's inspector)""",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-r', "--res", dest="resolution", default=None,
                        action="store",
                    help="Run at specified resolution, e.g. 1024 or 1024x1366")
    parser.add_argument('-f', "--fullscreen", dest="fullscreen", default=False,
                        action="store_true",
                        help="Run fullscreen regardless of screen size")
    parser.add_argument('-m', '--monitor', action="store", default=0,
                        dest="monitor", type=int,
                        help='Run fullscreen on this monitor number')
    parser.add_argument('-n', "--notes", dest="show_notes", default=True,
                        action="store_false",
                        help="No notes area")
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
        print("exception! excValue='%s'" % excValue)
        # logging.critical(''.join(traceback.format_tb(tracebackobj)))
        # logging.critical('{0}: {1}'.format(excType, excValue))
        traceback.print_exception(excType, excValue, tracebackobj)
    sys.excepthook = excepthook

    args = parse_args()

    app = QApplication(sys.argv)

    pv = PresoView(args.url, fullscreen=args.fullscreen, monitor=args.monitor,
                   resolution=args.resolution, show_notes=args.show_notes)
    pv.show()

    app.exec_()
