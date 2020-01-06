#!/usr/bin/env python3

# Copyright (C) 2019 by Akkana Peck.
# Share and enjoy under the GPL v2 or later.

"""A kiosk that shows HTML quotations (or any other content)
   taken from a list of HTML files, one quotation per file.
   cycling randomly through the quotations and displaying
   the content as large as possible in the available space.
   Quotation files are expected to be HTML snippets, not complete files;
   they will be inserted into a generated file one at a time.

   Uses qpreso.py for the display window.

   Adjust the CSS below to your own preferences.

   Example args:
     qquotekiosk.py -f -t 7 -j /path/to/jquery-min.js /path/to/myquotes*.html
"""


import sys
import os
import argparse
import random
from pathlib import Path

from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWidgets import QApplication, QShortcut, QDesktopWidget, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

from qpreso import PresoView

fittext_fmt = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
/* Without the next line, the body will be positioned considerably down
 * from the top of the HTML.
 */
* { margin: 0; border: 0; padding: 0; }

/* Try to avoid scrollbars */
html, body { height: 99%%; }

body {
  background-color: black; color: black;
  /* outline: green solid thin; */
}

/* Can't allow paragraphs to have a margin, because that mysteriously
 * makes the body move way down below the top of the html.
 * Padding seems to do that less, at least.
 */
p { padding-bottom: .75em; }

#quotecontent {
  /* More trying to avoid scrollbars */
  width: 90%%; height: 90%%;
  padding: 40px;
  /* outline: red solid thin; */
  margin: auto;
}
</style>

<script src="%s"></script>
</head>

<body>

<div id="quotecontent">
  <span>
%s
</span>
</div>

<script>
// https://stackoverflow.com/questions/24376897/fit-text-perfectly-inside-a-div-height-and-width-without-affecting-the-size-of
$.fn.resizeText = function (options) {

    var settings = $.extend({ maxfont: 200, minfont: 4 }, options);

    var style = $('<style>').html('.nodelays ' +
    '{ ' +
        '-moz-transition: none !important; ' +
        '-webkit-transition: none !important;' +
        '-o-transition: none !important; ' +
        'transition: none !important;' +
    '}');

    function shrink(el, fontsize, minfontsize)
    {
        if (fontsize < minfontsize) return;
        el.style.fontSize = fontsize + 'px';
        if (el.scrollHeight > el.offsetHeight) shrink(el, fontsize - 1, minfontsize);
    }

    $('head').append(style);

    $(this).each(function(index, el)
    {
        var element = $(el);
        element.addClass('nodelays');
        shrink(el, settings.maxfont, settings.minfont);
        element.removeClass('nodelays');
    });

    style.remove();
}

// The function to compute the font size is very slow.
// So the default color is set to black, and once resizeText() has run,
// it's okay to set the color to yellow to make it visible.
$(document).ready(function() {
  $(quotecontent).resizeText();
  $(quotecontent).css('color', 'yellow');
});
</script>

</body>
</html>'''


def parse_args():
    """Parse commandline arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--fullscreen", dest="fullscreen", default=False,
                        action="store_true",
                        help="Run fullscreen regardless of screen size")
    parser.add_argument('-m', '--monitor', action="store", default=-1,
                        dest="monitor", type=int,
                        help='Run fullscreen on this monitor')
    parser.add_argument('-t', '--time', action="store", default=30,
                        dest="time", type=int,
                        help='Time in seconds to pause between quotes')
    parser.add_argument('-j', '--jquerypath', action="store",
                        dest="jquerypath",
                        default="https://code.jquery.com/jquery-3.4.1.slim.min.js",
                        help='Path or URL to jquery-min.js file')
    parser.add_argument('quotefiles', nargs='+', help="HTML files of quotes")

    return parser.parse_known_args()[0]


# This timer function depends on the global variable args
# (see comment in main).
def new_page():
    global args
    if ':' not in args.jquerypath:
        args.jquerypath = 'file://%s' % Path(args.jquerypath).absolute()
    with open(random.choice(args.quotefiles)) as fp:
        minute = fp.read()
    tmpfile = '/tmp/100minute.html'
    with open(tmpfile, 'w') as fp:
        fp.write(fittext_fmt % (args.jquerypath, minute))

    tmpurl = 'file://' + tmpfile
    presoview.load(QUrl(tmpurl))


if __name__ == '__main__':

    # Qt provides no way to pass function arguments to callbacks like timers!
    # Of course it's possible to bind variables to a function object,
    # but that's way more work than using globals, so for now:
    global args, presoview, jquerydir

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

    presoview = PresoView('about:blank',
                          fullscreen=args.fullscreen, monitor=args.monitor)
    presoview.show()

    new_page()

    timer = QTimer(presoview)
    timer.timeout.connect(new_page)
    timer.start(args.time * 1000)

    app.exec_()
