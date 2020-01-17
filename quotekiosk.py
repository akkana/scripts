#! /usr/bin/env python3

"""Display a series of quotes in a large, maybe fullscreen, window,
   as large as possible to fit in the window, changing the quote
   every so often.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
import cairo
from gi.repository import Pango
from gi.repository import PangoCairo
from gi.repository import GdkPixbuf

import random
import re
from pathlib import Path

import html2text
# html2text adds line breaks unless told not to:
html_converter = html2text.HTML2Text()
html_converter.body_width = 0

IMAGE_EXTS = ( '.jpg', '.png', '.gif', '.tif' )

# Fraction of screen images should take up:
FILLFRAC = .95


def is_html_file(filename):
    filename = filename.lower()
    return filename.endswith('.html') or filename.endswith('.htm')


class AutoSizerWindow(Gtk.Window):
    """A window that can resize its content, either text or image,
       to fill as much space as possible.
    """
    def __init__(self, fullscreen=False, fontname="Serif Italic",
                 border_size=40):
        super(AutoSizerWindow, self).__init__()

        self.content_area = None

        self.fontname = fontname

        self.use_fullscreen = fullscreen
        if not fullscreen:
            self.width=1024
            self.height=768

        self.border_size = border_size

        self.background_color = (0, 0, 0)
        self.text_color = (1, 1, 0)

        self.content = "*"
        self.pixbuf = None

        self.content_area = Gtk.DrawingArea()

        self.add(self.content_area)

    def set_content(self, newcontent):
        self.pixbuf = None
        contentpath = Path(newcontent)
        if contentpath.exists():
            ext = contentpath.suffix.lower()
            if ext.startswith('.htm'):
                try:
                    with open(newcontent) as qf:
                        self.content = qf.read()
                    self.content = html_converter.handle(self.content)

                except Exception as e:
                    print("Couldn't read", newcontent, ":", e)
                    self.content = newcontent

            elif ext in IMAGE_EXTS:
                try:
                    self.prepare_image(newcontent)
                except Exception as e:
                    print("Couldn't open image", newcontent, ":", e)
                    self.content = newcontent

        self.content = self.content.strip()

    def show_window(self):
        if self.use_fullscreen:
            self.fullscreen()
        else:
            self.set_default_size(self.width, self.height)

        # self.connect("delete_event", Gtk.main_quit)
        self.content_area.connect('draw', self.draw)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key_press)

        self.show_all()

    def draw_text(self, paragraph, ctx):
        """Draw the text as large as can fit."""

        # Clear the page
        self.clear(ctx)
        ctx.set_source_rgb(*self.text_color)

        layout = PangoCairo.create_layout(ctx)
        layout.set_text(paragraph, -1)

        # For some reason pango width has to be 1024 times the width.
        # Why? Where does this 1024 come from?
        # No one explains this anywhere.
        layout.set_width(1024 * (self.width - self.border_size*2))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)

        fontsize = 100

        while fontsize:
            font = f"{self.fontname} {fontsize}"
            desc = Pango.font_description_from_string(font)
            layout.set_font_description(desc)
            pxsize = layout.get_pixel_size()
            if pxsize.width < self.width - self.border_size*2 and \
               pxsize.height < self.height - self.border_size*2:
                break
            fontsize -= 1

        ctx.move_to(self.border_size, self.border_size)
        PangoCairo.show_layout (ctx, layout)
        # self.ctx.show_text(label)

    def prepare_image(self, filename):
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
        imgW = self.pixbuf.get_width()
        imgH = self.pixbuf.get_height()

        # Check aspect ratios:
        if imgW/imgH > self.width/self.height:
            # image has a wider aspect ratio than window; scale by width
            newW = self.width * FILLFRAC;
            newH = imgH * self.width / imgW * FILLFRAC;
        else:
            # image has a narrower aspect ratio than window; scale by height
            newH = self.height * FILLFRAC;
            newW = imgW * self.height / imgH * FILLFRAC;

        self.pixbuf = self.pixbuf.scale_simple(newW, newH,
                                               GdkPixbuf.InterpType.BILINEAR)

    def draw_image(self, ctx):
        imgW = self.pixbuf.get_width()
        imgH = self.pixbuf.get_height()
        x = (self.width - imgW) / 2
        y = (self.height - imgH) / 2

        self.clear(ctx)
        Gdk.cairo_set_source_pixbuf(ctx, self.pixbuf, x, y)

        ctx.paint()

    def clear(self, ctx):
        """Clear the screen. XXX eventually this should fade.
        """
        ctx.set_source_rgb(*self.background_color)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()

    def draw(self, widget, ctx):
        """Draw everything."""

        self.clear(ctx)

        # Get the size every time: window may have changed.
        self.width, self.height = self.get_size()

        if self.pixbuf:
            self.draw_image(ctx)
        else:
            self.draw_text(self.content, ctx)

    def key_press(self, widget, event):
        """Handle a key press event anywhere in the window"""

        if event.keyval == Gdk.KEY_q:
            Gtk.main_quit()
            return

        return False


class KioskWindow(AutoSizerWindow):
    def __init__(self, fullscreen=False, fontname="Serif Italic",
                 border_size=40, timeout=30):
        super(KioskWindow, self).__init__(fullscreen,
                                          fontname=fontname,
                                          border_size=border_size)
        self.timeout = timeout

        # quote_list can be a mixture of quotes and filenames
        self.quote_list = []

        print("Setting a timeout of time", self.timeout * 1000)
        GLib.timeout_add(self.timeout * 1000, self.timeout_cb)

    def new_quote(self):
        choice = random.choice(self.quote_list)
        print("choice", choice)

        self.set_content(choice)

        self.content_area.queue_draw()

    def add_content(self, newcontent):
        """Set the quotes that will be displayed.
           newcontent is a list of strings, quotes or filenames or both.
        """
        self.quote_list += newcontent

        self.new_quote()

    def timeout_cb(self):
        self.new_quote()

        # Returning True keeps the timeout in effect; no need to set a new one.
        return True


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--fullscreen", dest="fullscreen",
                        action="store_true", default=False,
                        help="Run fullscreen regardless of screen size")
    parser.add_argument('-t', '--time', action="store",
                        dest="time", type=int, default=30,
                        help='Time in seconds to pause between quotes')
    parser.add_argument('quotes', nargs='+', help="Quotes, or files of quotes")
    args = parser.parse_args(sys.argv[1:])

    win = KioskWindow(fullscreen=args.fullscreen, timeout=args.time)

    win.add_content(args.quotes)

    win.show_window()
    Gtk.main()

