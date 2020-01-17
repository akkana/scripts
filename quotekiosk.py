#! /usr/bin/env python3

"""Display a series of quotes in a large, maybe fullscreen, window,
   as large as possible to fit in the window, changing the quote
   every so often.
"""

# On Debian/Raspbian/Ubuntu, requires:
# python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-html2text

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
import gc
from pathlib import Path

import html2text
# html2text adds line breaks unless told not to:
html_converter = html2text.HTML2Text()
html_converter.body_width = 0

IMAGE_EXTS = ( '.jpg', '.jpeg', '.png', '.gif', '.tif' )

# Fraction of screen images should take up:
FILLFRAC = .95

# How many pixbufs can be allocated before garbage collecting?
PIXBUFS_BEFORE_GC = 2

# Fade parameters
FADE_FRAC = .02
FADE_TIMEOUT = 60     # milliseconds


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
        if fullscreen:
            self.width = 0
            self.height = 0
        else:
            self.width = 1024
            self.height = 768

        self.border_size = border_size

        self.background_color = (0, 0, 0)
        self.text_color = (1, 1, 0)

        # alpha to be used for fades
        self.alpha = 1
        self.d_alpha = 0

        self.content = "*"
        self.pixbuf = None

        # How many pixbufs have we allocated?
        # gdk-pixbuf doesn't handle its own garbage collection.
        self.pixbuf_count = 0

        self.content_area = Gtk.DrawingArea()

        self.add(self.content_area)

    def set_content(self, newcontent):
        """Change the text or image being displayed.
           Initiate fading, if any.
        """
        self.pixbuf = None

        # garbage collect the old pixbuf, if any, and the one we just read in.
        # GTK doesn't do its own garbage collection.
        if self.pixbuf_count > PIXBUFS_BEFORE_GC:
            gc.collect()
            self.pixbuf_count = 0

        contentpath = Path(newcontent)
        if contentpath.exists():
            ext = contentpath.suffix.lower()
            if ext.startswith('.htm'):
                try:
                    with open(newcontent) as qf:
                        self.content = qf.read()
                    self.content = html_converter.handle(self.content)

                except FileNotFoundError as e:
                    print("Couldn't read", newcontent, ":", e)
                    self.content = newcontent

            elif ext in IMAGE_EXTS:
                try:
                    self.read_pixbuf(newcontent)
                    self.content = ''
                except gi.repository.GLib.Error as e:
                    print("Couldn't open image", newcontent, ":", e)
                    self.content = newcontent

        if self.content:
            self.content = self.content.strip()

    def draw(self, widget, ctx):
        """Draw everything."""

        self.clear(ctx)

        # Get the size every time: window may have changed.
        self.width, self.height = self.get_size()

        if self.pixbuf:
            self.draw_image(ctx)
        else:
            self.draw_text(self.content, ctx)

    def draw_text(self, paragraph, ctx):
        """Draw the text as large as can fit."""

        # Clear the page
        self.clear(ctx)

        # Set color and alpha
        ctx.set_source_rgba(*self.text_color, self.alpha)

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
        PangoCairo.show_layout(ctx, layout)

    def read_pixbuf(self, filename):
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
        self.pixbuf_count += 1

    def resize_image(self):
        if not self.pixbuf:
            print("Yikes, resize_image called with no pixbuf!")
            return

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
        """Resize and draw the pixbuf."""

        self.resize_image()

        imgW = self.pixbuf.get_width()
        imgH = self.pixbuf.get_height()
        x = (self.width - imgW) / 2
        y = (self.height - imgH) / 2

        self.clear(ctx)
        Gdk.cairo_set_source_pixbuf(ctx, self.pixbuf, x, y)

        ctx.paint_with_alpha(self.alpha)

    def clear(self, ctx):
        """Clear the screen. XXX eventually this should fade.
        """
        ctx.set_source_rgb(*self.background_color)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()

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

        GLib.timeout_add(self.timeout * 1000, self.timeout_cb)

    def new_quote(self):
        # Fade out
        self.d_alpha = -FADE_FRAC
        GLib.timeout_add(FADE_TIMEOUT, self.fade_cb)

        choice = random.choice(self.quote_list)
        print("*** New choice", choice)

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

    def fade_cb(self):

        # Adjust fade
        self.alpha += self.d_alpha
        if self.alpha <= 0:
            self.alpha = 0
            self.d_alpha = FADE_FRAC
        elif self.alpha >= 1:
            self.alpha = 1
            self.d_alpha = 0

        self.content_area.queue_draw()

        if self.d_alpha:
            return True
        return False


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

