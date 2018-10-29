#!/usr/bin/env python3

# Copyright (C) 2018 by Akkana Peck.
# Share and enjoy under the GPL v2 or later.

'''A simple private browser.'''

import os
import sys
import traceback
import posixpath
import socket
import select
import argparse

from PyQt5.QtCore import QUrl, Qt, QEvent, QSocketNotifier
from PyQt5.QtWidgets import QApplication, QMainWindow, QToolBar, QAction, \
     QLineEdit, QStatusBar, QProgressBar, QTabWidget, QShortcut, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, \
     QWebEngineProfile, QWebEngineSettings
from PyQt5.QtCore import QAbstractNativeEventFilter

# Use qpdfview for PDFs if it's available:
try:
    import qpdfview
    handle_pdf = True
except:
    handle_pdf = False

def is_pdf(url):
    if not url:
        return False
    return handle_pdf and url.lower().endswith('.pdf')

# The socket used to send remote commands:
CMD_PIPE = "/tmp/quickbrowse-%d"

# How long can a tab name be?
MAX_TAB_NAME = 22

class ReadlineEdit(QLineEdit):
    def __init__(self):
        super (ReadlineEdit, self).__init__()

    def keyPressEvent(self, event):
        # http://pyqt.sourceforge.net/Docs/PyQt4/qt.html#Key-enum
        if (event.modifiers() & Qt.ControlModifier):
            k = event.key()
            if k == Qt.Key_Control:
                return
            if k == Qt.Key_A:
                self.home(False)
            elif k == Qt.Key_E:
                self.end(False)
            elif k == Qt.Key_B:
                self.cursorBackward(False, 1)
            elif k == Qt.Key_F:
                self.cursorForward(False, 1)
            elif k == Qt.Key_H:
                self.backspace()
            elif k == Qt.Key_D:
                self.del_()
            elif k == Qt.Key_W:
                self.cursorWordBackward(True)
                self.del_()
            elif k == Qt.Key_U:
                self.clear()
            return

        # For anything else, call the base class.
        super(ReadlineEdit, self).keyPressEvent(event)

# Only define the PDFBrowserView if we have the modules it requires.
if handle_pdf:
    class PDFBrowserView(qpdfview.PDFScrolledWidget):
        def __init__(self, browserwin, url, parent=None):
            if url.startswith('file://'):
                self.theurl = url[7:]
            else:
                self.theurl = url

            super(PDFBrowserView, self).__init__(self.theurl, parent=parent)

        def url(self):
            return QUrl(self.theurl)

        def toDisplayString(self):
            return self.url

# Need to subclass QWebEngineView, in order to have an object that
# can own each load_finished() callback and have a pointer to
# the main BrowserWindow so it can figure out which tab is loading.
class BrowserView(QWebEngineView):
    def __init__(self, browserwin, *args, **kwargs):

        # Strip out arguments we handle that are different from QMainWindow:
        if 'width' in kwargs:
            self.width = kwargs['width']
            del kwargs['width']
        else:
            self.width = 1024
        if 'height' in kwargs:
            self.height = kwargs['height']
            del kwargs['height']
        else:
            self.height = 768

        if 'parent' in kwargs:
            super(BrowserView, self).__init__(kwargs['parent'])
        else:
            super(BrowserView, self).__init__()

        self.settings().defaultSettings().setDefaultTextEncoding("utf-8")

        QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

        self.browser_win = browserwin

        self.installEventFilter(self)

        # ICK! I can't find any way to intercept a middle click and get
        # the URL under the mouse during the click. But we do get hover
        # events -- so if we always record the last hovered URL,
        # then when we see a middleclick we can load that URL.
        self.last_hovered = None

        # Another ICK -- there's no reliable way to get URL loading
        # errors, so we'll store URLs we try to load, and compare
        # after load_finished to see if we're in the right place.
        self.try_url = None

    def eventFilter(self, source, event):
        if (event.type() == QEvent.ChildAdded and source is self
            and event.child().isWidgetType()):
            self._glwidget = event.child()
            self._glwidget.installEventFilter(self)
            # return super().eventFilter(source, event)
            return True

        # Middle click, not over a link: load the selection.
        # XXX This prevents pasting into text fields too. Must fix.
        elif event.type() == QEvent.MouseButtonPress and \
             event.button() == Qt.MidButton and not self.last_hovered:
                # if self.last_hovered:
                #     self.browser_win.new_tab(self.last_hovered)
                # else:
            qc = QApplication.clipboard()
            self.browser_win.load_url(qc.text(mode=qc.Selection))
            return True

        return super().eventFilter(source, event)

    def createWindow(self, wintype):
        # Possible values for wintype: WebBrowserWindow, WebBrowserTab,
        # WebDialog, WebBrowserBackgroundTab, all attributes of QWebEnginePage.
        # Right now, though, we're ignoring type and making a new background
        # tab in all cases.
        self.browser_win.new_tab()
        return self.browser_win.browserviews[-1]

    # Override the context menu event so we can copy the clipboard
    # selection to primary after a "Copy Link URL" action.
    # Qt5 only copies it to Clipboard, making X primary paste impossible.
    def contextMenuEvent(self, event):
        menu = self.page().createStandardContextMenu()

        # In theory we could loop over actions, find one and change it.
        # for action in menu.actions():
        #     print("Action", action.text())
        #     if action.text().startswith("Copy Link"):
        #         pass
        # You can also apparently change an action with
        # action.triggered.connect(qApp.quit)

        action = menu.exec_(event.globalPos())
        if (action and action.text().startswith("Copy")):
            # Copy clipboard text to the primary selection:
            qc = QApplication.clipboard()
            qc.setText(qc.text(qc.Clipboard), qc.Selection)

    #
    # Slots
    #

    def url_changed(self, url):
        # I can't find any way to find out about load errors.
        # But an attempted load that fails gives a url_changed(about:blank)
        # so maybe we can detect it that way.
        tabname = url.toDisplayString()[:MAX_TAB_NAME]
        self.browser_win.set_tab_text(tabname, self)

        if not url or 'blank' in url.toString():
            self.browser_win.statusBar().showMessage("Couldn't load '%s'" %
                                                     self.try_url)
            return

        if self.browser_win.browserviews[self.browser_win.active_tab] != self:
            return

        urlbar = self.browser_win.urlbar
        urlbar.setText(url.toDisplayString())

    def link_hover(self, url):
        self.browser_win.statusBar().showMessage(url)
        self.last_hovered = url

    def load_started(self):
        # Setting the default encoding in __init__ doesn't do anything;
        # it gets reset as soon as we load a page.
        # There's no documentation on where it's supposed to be set,
        # but setting it here seems to work.
        # self.settings().setDefaultTextEncoding("utf-8")

        self.browser_win.progress.show()

        # If the link is PDF, the WebEngineView won't do anything with it,
        # but also doesn't give any obvious way to divert it.
        # Maybe open a new tab for it here:
        # But last_hovered isn't enough, we might be starting a load
        # from a commandline argument or other means.
        # How do we find out the URL being loaded?

    def load_finished(self, ok):
        # OK is useless: if we try to load a bad URL, we won't get a
        # loadFinished on that; instead it will switch to about:blank,
        # load that successfully and call loadFinished with ok=True.
        self.browser_win.progress.hide()
        url = self.browser_win.browserviews[self.browser_win.active_tab].url().toString()
        self.browser_win.progress.hide()
        if not ok or not url:
            if not url:
                url = self.try_url
            load_failed_error = '''<br><br><br><br><big>" \
                "Yikes! Load failed for %s</big>''' % url
            view = self.browser_win.browserviews[self.browser_win.active_tab]
            view.setHtml(load_failed_error)

        # print("load_finished")
        # print("In load_finished, view is", self.browserviews[self.active_tab], "and page is", self.browserviews[self.active_tab].page())
        # print("Profile off the record?", self.profile.isOffTheRecord())
        # print("Webpage off the record?", self.browserviews[self.active_tab].page().profile().isOffTheRecord())

        tabname = self.title()[:MAX_TAB_NAME]
        self.browser_win.set_tab_text(tabname, self)

        self.browser_win.focus_content()

    def load_progress(self, progress):
        self.browser_win.progress.setValue(progress)

    def zoom(self, factor=1.25):
        self.setZoomFactor(self.zoomFactor() * factor)

    def unzoom(self, factor=.8):
        self.zoom(factor)

class BrowserPage(QWebEnginePage):
    def __init__(self, profile, browser_view, browser_window):
        self.browser_view = browser_view
        self.browser_window = browser_window
        super(BrowserPage, self).__init__(profile)

        self.fullScreenRequested.connect(self.fullscreen_requested)

    # Override all the chatty JS warnings:
    def javaScriptConsoleMessage(level, message, lineNumber, sourceID):
        pass

    def acceptNavigationRequest(self, url, navtype, isMainFrame):
        # isMainFrame is false for a link in an iframe.
        # navtype is something like QWebEnginePage.NavigationTypeLinkClicked:
        # print("acceptNavigationRequest", url, navtype, isMainFrame)

        if not isMainFrame:
            return True

        urlpath = url.path()
        if urlpath.lower().endswith('.pdf'):
            self.browser_window.load_url(url.toString(), 0)
            return False

        return True

    def fullscreen_requested(self, request):
        request.accept()
        if request.toggleOn():
            self.browser_window.showFullScreen()
        else:
            self.browser_window.showNormal()

class BrowserWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        # Strip out arguments we handle that are different from QMainWindow:
        if 'width' in kwargs:
            self.width = kwargs['width']
            del kwargs['width']
        else:
            self.width = 1024
        if 'height' in kwargs:
            self.height = kwargs['height']
            del kwargs['height']
        else:
            # Short enough to fit in XGA, 768 height:
            self.height = 735

        # Then run the default constructor.
        super(BrowserWindow, self).__init__(*args, **kwargs)

        self.browserviews = []

        self.profile = QWebEngineProfile()
        # print("Profile initially off the record?",
        #       self.profile.isOffTheRecord())

        self.init_tab_name_len = 40

        self.init_chrome()

        # Resize to fit on an XGA screen, allowing for window chrome.
        # XXX Should check the screen size and see if it can be bigger.
        self.resize(self.width, self.height)

        # Set up the listener for remote commands, the filename
        # and the buffer where we'll store those commands:
        self.cmdsockname = None
        self.cmdread = b''
        self.set_up_listener()

    # Each process has one BrowserWindow, and each BrowserWindow has one
    # command pipe (a Unix-domain socket) where it can accept commands.
    def set_up_listener(self):
        # Make sure the socket does not already exist
        self.cmdsockname = CMD_PIPE % os.getpid()
        try:
            os.unlink(self.cmdsockname)
        except OSError:
            if os.path.exists(self.cmdsockname):
                raise

        # Create a UDS socket
        self.cmdsock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # Bind the socket to the port
        self.cmdsock.bind(self.cmdsockname)

        # Listen for incoming connections
        self.cmdsock.listen(1)

        self.notifier = QSocketNotifier(self.cmdsock.fileno(),
                                        QSocketNotifier.Read)

        self.notifier.activated.connect(self.pipe_ready)

    def pipe_ready(self):
        connection, client_address = self.cmdsock.accept()
        with connection:
            try:
                while True:
                    data = connection.recv(1024)
                    if not data: break
                    self.cmdread += data

            finally:
                # Clean up the connection
                connection.close()

        # Commands end with newlines.
        # Figure out how many commands we've read, if any.
        # It's possible to read more than one command at once,
        # or that we don't yet have all the data even for a single command.
        cmdlines = self.cmdread.split(b'\n')
        if self.cmdread.endswith(b'\n'):
            self.cmdread = b''
        else:
            # Our last command is incomplete; we'll have to wait
            # for the rest of the line to come through.
            self.cmdread = cmdlines[-1]
            cmdlines = cmdlines[:-1]

        for cmd in cmdlines:
            if not cmd:
                continue
            # Change it from bytes to string:
            cmd = cmd.decode('utf-8')
            if cmd.startswith('new-tab ') and len(cmd) > 8:
                self.new_tab(cmd[8:])

    @staticmethod
    def send_command(cmd, url):
        '''Send a command to a running quickbrowse process.
           This will usually be called from a separate, new, process.
        '''
        # Start by finding the available CMD_PIPEs.
        # We'll use the one with the most recent ctime.
        pipedir, sockbase = os.path.split(CMD_PIPE)
        # Split off any %d in sockbase
        if '%' in sockbase:
            sockbase = sockbase[:sockbase.find('%')]
        flist = os.listdir(pipedir)
        cmdsockname = ""  # This tests as less than any real string
        last_ctime = 0
        for f in flist:
            if f.startswith(sockbase):
                sockname = os.path.join(pipedir, f)
                this_ctime = os.path.getctime(sockname)
                if this_ctime > last_ctime:
                    cmdsockname = sockname
                    last_ctime = this_ctime

        if not cmdsockname:
            raise IOError("No running quickbrowse process")

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # Next line can raise socket.err, especially if there's no listener,
        # but rather than catching them, we'll raise it
        # and the caller can use that to decide to open a new window.
        sock.connect(cmdsockname)

        try:
            sock.sendall(b"%s %s\n" % (cmd.encode('utf-8'),
                                       url.encode('utf-8')))

        finally:
            sock.close()

    def init_chrome(self):
        # Set up the browser window chrome:
        self.setWindowTitle("Quickbrowse")

        toolbar = QToolBar("Toolbar")
        self.addToolBar(toolbar)

        btn_act = QAction("Back", self)
        # for an icon: QAction(QIcon("bug.png"), "Your button", self)
        btn_act.setStatusTip("Go back")
        btn_act.triggered.connect(self.go_back)
        toolbar.addAction(btn_act)

        btn_act = QAction("Forward", self)
        btn_act.setStatusTip("Go forward")
        btn_act.triggered.connect(self.go_forward)
        toolbar.addAction(btn_act)

        btn_act = QAction("Reload", self)
        btn_act.setStatusTip("Reload")
        btn_act.triggered.connect(self.reload)
        toolbar.addAction(btn_act)

        self.urlbar = ReadlineEdit()
        self.urlbar.setPlaceholderText("URL goes here")
        self.urlbar.returnPressed.connect(self.urlbar_load)
        toolbar.addWidget(self.urlbar)

        self.tabwidget = QTabWidget()
        self.tabwidget.setTabBarAutoHide(True)

        self.setCentralWidget(self.tabwidget)

        self.tabwidget.tabBar().installEventFilter(self)
        self.prev_middle = -1
        self.active_tab = 0

        self.setStatusBar(QStatusBar(self))
        self.progress = QProgressBar()
        self.statusBar().addPermanentWidget(self.progress)

        # Key bindings
        # For keys like function keys, use QtGui.QKeySequence("F12")
        QShortcut("Ctrl+Q", self, activated=self.close)
        QShortcut("Ctrl+L", self, activated=self.select_urlbar)
        QShortcut("Ctrl+T", self, activated=self.new_tab)
        QShortcut("Ctrl+R", self, activated=self.reload)

        QShortcut("Ctrl++", self, activated=self.zoom)
        QShortcut("Ctrl+=", self, activated=self.zoom)
        QShortcut("Ctrl+-", self, activated=self.unzoom)

        QShortcut("Alt+Left", self, activated=self.go_back)
        QShortcut("Alt+Right", self, activated=self.go_forward)

        QShortcut("Esc", self, activated=self.unfullscreen)

    def eventFilter(self, object, event):
        '''Handle button presses in the tab bar'''

        if object != self.tabwidget.tabBar():
            print("eventFilter Not in tab bar")
            return super().eventFilter(object, event)
            # return False

        if event.type() not in [QEvent.MouseButtonPress,
                                QEvent.MouseButtonRelease]:
            # print("Not a button press or release", event)
            return super().eventFilter(object, event)
            # return False

        tabindex = object.tabAt(event.pos())

        if event.button() == Qt.LeftButton:
            if event.type() == QEvent.MouseButtonPress:
                self.active_tab = tabindex
                self.urlbar.setText(self.browserviews[tabindex].url().toDisplayString())
            return super().eventFilter(object, event)
            # return False    # So we'll still switch to that tab

        if event.button() == Qt.MidButton:
            if event.type() == QEvent.MouseButtonPress:
                    self.prev_middle = tabindex
            else:
                if tabindex != -1 and tabindex == self.prev_middle:
                    self.close_tab(tabindex)
                self.prev_middle = -1
            return True

        print("Unknown button", event)
        return super().eventFilter(object, event)

    def new_tab(self, url=None):
        if url:
            init_name = url[:self.init_tab_name_len]
        else:
            init_name = "New tab"

        if is_pdf(url):
            webview = PDFBrowserView(self, url)
            self.browserviews.append(webview)
            self.tabwidget.addTab(webview, init_name)

        else:    # The normal case, an HTML page
            webview = BrowserView(self)

            # We need a QWebEnginePage in order to get linkHovered events,
            # and to set an anonymous profile.
            # print("New tab, profile still off the record?",
            #       self.profile.isOffTheRecord())
            webpage = BrowserPage(self.profile, webview, self)

            # print("New Webpage off the record?",
            #       webpage.profile().isOffTheRecord())
            webview.setPage(webpage)
            # print("New view's page off the record?",
            #       webview.page().profile().isOffTheRecord())
            # print("In new tab, view is", webview, "and page is", webpage)

            self.browserviews.append(webview)
            self.tabwidget.addTab(webview, init_name)

            if url:
                self.load_url(url, len(self.browserviews)-1)

            # Set up the signals:
            webview.urlChanged.connect(webview.url_changed)
            webview.loadStarted.connect(webview.load_started)
            webview.loadFinished.connect(webview.load_finished)
            webview.loadProgress.connect(webview.load_progress)
            webpage.linkHovered.connect(webview.link_hover)

        return webview

    def focus_content(self):
        self.browserviews[self.active_tab].setFocus()

    def closeEvent(self, event):
        # Clean up
        if self.cmdsockname:
            os.unlink(self.cmdsockname)

    def close_tab(self, tabindex):
        self.tabwidget.removeTab(tabindex)

    def load_url(self, url, tab=None):
        '''Load the given URL in the specified tab, or current tab if tab=None.
           url is a str, not a QUrl.
           PDF URLs will be loaded in a new tab, because there doesn't
           seem to be a way of replacing the BrowserView with a BrowserPDFView.
        '''

        # If there are newlines, remove newlines plus all adjacent whitespace.
        if '\n' in url:
            lines = url.split('\n')
            url = ''.join([ l.strip() for l in lines ])

        # Note that tab=0 is a valid argument here.
        # When testing whether tab is set, be sure to test for None.

        if is_pdf(url):
            self.new_tab(url)
            return

        qurl = QUrl(url)

        if not qurl.scheme():
            if os.path.exists(url):
                qurl.setScheme('file')
                if not os.path.isabs(url):
                    # Is it better to use posixpath.join or os.path.join?
                    # Both work on Linux.
                    qurl.setPath(os.path.normpath(os.path.join(os.getcwd(),
                                                               url)))
            else:
                qurl.setScheme('http')

        if len(self.browserviews) == 0:
            self.new_tab()
            tab = 0
        elif tab == None:
            tab = self.active_tab

        self.set_tab_text(url[:self.init_tab_name_len],
                          self.browserviews[tab])
        if tab == self.active_tab:
            self.urlbar.setText(url)

        self.browserviews[tab].load(qurl)

    def load_html(self, html, base=None):
        '''Load a string containing HTML.
           The base is the file: URL the HTML should be considered to have
           come from, to avoid "Not allowed to load local resource" errors
           when clicking on links.
        '''
        if not self.browserviews:
            self.new_tab()
            tab = 0
        else:
            tab = self.active_tab
            self.set_tab_text("---",  # XXX Replace with html title if possible
                              self.browserviews[tab])

        self.browserviews[tab].setHtml(html, QUrl(base))

    def select_urlbar(self):
        self.urlbar.selectAll()
        self.urlbar.setFocus()

    def find_view(self, view):
        for i, v in enumerate(self.browserviews):
            if v == view:
                return i
        return None

    def set_tab_text(self, title, view):
        '''Set tab and, perhaps, window title after a page load.
           view is the requesting BrowserView, and will be compared
           to our browserviews[] to figure out which tab to set.
        '''
        if self.tabwidget == None:
            return
        whichtab = None
        whichtab = self.find_view(view)
        if whichtab == None:
            print("Warning: set_tab_text for unknown view")
            return
        self.tabwidget.setTabText(whichtab, title)

    def zoom(self):
        if 'zoom' in dir(self.browserviews[self.active_tab]):
            self.browserviews[self.active_tab].zoom()

    def unzoom(self):
        if 'unzoom' in dir(self.browserviews[self.active_tab]):
            self.browserviews[self.active_tab].unzoom()

    def unfullscreen(self):
        if self.isFullScreen():
            self.showNormal()

            # Some pages, like YouTube, want to know when the browser comes
            # out of fullscreen mode so it can adjust its chrome.
            self.browserviews[self.active_tab].page().triggerAction(QWebEnginePage.ExitFullScreen)

    def update_buttons(self):
        # TODO: To enable/disable buttons, check e.g.
        # self.webview.page().action(QWebEnginePage.Back).isEnabled())
        pass

    #
    # Slots
    #

    def urlbar_load(self):
        url = self.urlbar.text()
        self.load_url(url)

    def go_back(self):
        self.browserviews[self.active_tab].back()

    def go_forward(self):
        self.browserviews[self.active_tab].forward()

    def reload(self):
        self.browserviews[self.active_tab].reload()

def run_browser():

    #
    # PyQt is super crashy. Any little error, like an extra argument in a slot,
    # causes it to kill Python with a core dump.
    # Setting sys.excepthook works around this behavior,
    # and execution continues.
    #
    def excepthook(excType=None, excValue=None, tracebackobj=None, *,
                   message=None, version_tag=None, parent=None):
        # print("exception! excValue='%s'" % excValue)
        # logging.critical(''.join(traceback.format_tb(tracebackobj)))
        # logging.critical('{0}: {1}'.format(excType, excValue))
        traceback.print_exception(excType, excValue, tracebackobj)

    sys.excepthook = excepthook

    def parse_args():
        """Parse commandline arguments."""
        parser = argparse.ArgumentParser()

        parser.add_argument('-t', "--new-tab", dest="new_tab", default=False,
                            action="store_true", help="Open URLs in a new tab")

        parser.add_argument('url', nargs='*', help="URLs to open")

        return parser.parse_args(sys.argv[1:])

    def get_procname(procargs):
        '''Return the program name: either the first commandline argument,
           or, if that argument is some variant of "python", the second.
        '''
        basearg = os.path.basename(procargs[0])
        if basearg.startswith('python'):
            basearg = os.path.basename(procargs[1])
        return basearg
    progname = get_procname(sys.argv)

    def find_proc_by_name(name):
        """Looks for a process with the given basename, ignoring a possible
           "python" prefix in case it's another Python script.
           Will ignore the current running process.
           Returns the pid, or None.
        """
        PROCDIR = '/proc'
        for proc in os.listdir(PROCDIR):
            if not proc[0].isdigit():
                continue
            # Race condition: processes can come and go, so we may not be
            # able to open something just because it was there when we
            # did the listdir.
            try:
                with open(os.path.join(PROCDIR, proc, 'cmdline')) as procfp:
                    procargs = procfp.read().split('\0')
                    basearg = get_procname(procargs)
                    if basearg == name and int(proc) != os.getpid():
                        return int(proc)
            except Exception as e:
                print("Exception", e)
                pass
        return None

    args = parse_args()

    if args.new_tab:
        # Try to use an existing instance of quickbrowse
        # instead of creating a new window.
        # XXX This should be in a try, and then fall through if no answer.
        try:
            for url in args.url:
                if args.new_tab:
                    BrowserWindow.send_command("new-tab", url)

            sys.exit(0)
        except Exception as e:
            print("No existing %s process: starting a new one." % progname)

    # Return control to the shell before creating the window:
    rc = os.fork()
    if rc:
        sys.exit(0)

    app = QApplication(sys.argv)

    win = BrowserWindow()
    for url in args.url:
        win.new_tab(url)
    win.show()

    app.exec_()

def run_main_quietly():
    # Suppress stderr, because QtWebEngine, DBus etc.print so much
    # warning chatter.
    # https://stackoverflow.com/questions/5081657/how-do-i-prevent-a-c-shared-library-to-print-on-stdout-in-python
    from contextlib import contextmanager

    @contextmanager
    def stderr_redirected(to=os.devnull):
        '''
        import os

        with stderr_redirected(to=filename):
            print("from Python")
            os.system("echo non-Python applications are also supported")
        '''
        fd = sys.stderr.fileno()

        def _redirect_stderr(to):
            sys.stderr.close() # + implicit flush()
            os.dup2(to.fileno(), fd) # fd writes to 'to' file
            sys.stderr = os.fdopen(fd, 'w') # Python writes to fd

        with os.fdopen(os.dup(fd), 'w') as old_stderr:
            with open(to, 'w') as file:
                _redirect_stderr(to=file)
            try:
                yield # allow code to be run with the redirected stderr
            finally:
                _redirect_stderr(to=old_stderr) # restore stdout.
                                                # buffering and flags such as
                                                # CLOEXEC may be different

    with stderr_redirected():
        run_browser()

if __name__ == '__main__':
    run_main_quietly()
