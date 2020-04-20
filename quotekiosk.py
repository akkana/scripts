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

# import html2text
# # html2text adds line breaks unless told not to:
# html_converter = html2text.HTML2Text()
# html_converter.body_width = 0

IMAGE_EXTS = ( '.jpg', '.jpeg', '.png', '.gif', '.tif' )

# Fraction of screen images should take up:
FILLFRAC = .95

# How many pixbufs can be allocated before garbage collecting?
PIXBUFS_BEFORE_GC = 2

# Fade parameters. Set FADE_FRAC to 0 for no fading.
FADE_FRAC = .02
FADE_TIMEOUT = 60     # milliseconds


def is_html_file(filename):
    filename = filename.lower()
    return filename.endswith('.html') or filename.endswith('.htm')


class AutoSizerWindow(Gtk.Window):
    """A window that can resize its content, either text or image,
       to fill as much space as possible.
    """
    def __init__(self, fullscreen=False, fadetime=2, fontname="Serif",
                 colors='yellow:black', border_size=40):
        super().__init__()

        self.content_area = None

        self.fontname = fontname
        self.fontdesc = Pango.FontDescription(fontname)

        self.use_fullscreen = fullscreen
        if fullscreen:
            self.width = 0
            self.height = 0
        else:
            self.width = 1024
            self.height = 768

        # From the desired total fade time, calculate fade delay in
        # milliseconds, and what fraction to fade during that time.
        if fadetime:
            self.fademillis = 50
            self.fadefrac = fadetime / self.fademillis
        else:
            self.fademillis = 0
            self.fadefrac = 0

        self.border_size = border_size

        if colors:
            self.background_color = (0, 0, 0)
            self.text_color = (1, 1, 0)
        else:
            self.parse_colors(colors)

        # alpha to be used for fades
        self.alpha = 1
        self.d_alpha = 0

        self.content = ""
        self.imagefile = None
        self.pixbuf = None
        self.layout = None

        # How many pixbufs have we allocated?
        # gdk-pixbuf doesn't handle its own garbage collection.
        self.pixbuf_count = 0

        self.content_area = Gtk.DrawingArea()

        self.add(self.content_area)

    def set_content(self, newcontent):
        """Change the text or image being displayed.
           Initiate fading, if any.
        """
        self.layout = None
        self.pixbuf = None
        self.imagefile = None
        self.content = ""

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
                        # self.content = html_converter.handle(self.content)

                except FileNotFoundError as e:
                    print("Couldn't read", newcontent, ":", e)
                    self.content = newcontent

            elif ext in IMAGE_EXTS:
                self.imagefile = newcontent

        else:
            self.content = newcontent

        if self.content:
            self.content = self.content.strip()

    def draw(self, widget, ctx):
        """Draw everything."""

        self.clear(ctx)

        # Get the size every time: window may have changed.
        self.width, self.height = self.get_size()

        if self.pixbuf or self.imagefile:
            self.draw_image(ctx)
        else:
            self.draw_text(ctx)

    def draw_text(self, ctx):
        """Draw the text as large as can fit."""

        # Clear the page
        self.clear(ctx)

        # Set color and alpha
        ctx.set_source_rgba(*self.text_color, self.alpha)

        if not self.layout: # or not self.d_alpha or self.alpha == 0:
            self.layout = PangoCairo.create_layout(ctx)
            # self.layout.set_text(self.content, -1)
            self.layout.set_markup(self.content, -1)

            # For some reason pango width has to be 1024 times the width.
            # Why? Where does this 1024 come from?
            # No one explains this anywhere.
            self.layout.set_width(1024 * (self.width - self.border_size*2))
            self.layout.set_wrap(Pango.WrapMode.WORD_CHAR)

            fontsize = 300

            while fontsize:
                font = f"{self.fontname} {fontsize}"
                desc = Pango.font_description_from_string(font)
                self.layout.set_font_description(desc)
                pxsize = self.layout.get_pixel_size()
                if pxsize.width < self.width - self.border_size*2 and \
                   pxsize.height < self.height - self.border_size*2:
                    break
                fontsize -= 1

        ctx.move_to(self.border_size, self.border_size)

        PangoCairo.show_layout(ctx, self.layout)

    def setup_image(self):
        """Read self.imagefile into a pixbuf, and scale it to the screen.
        """
        # print("setting up image", self.imagefile)

        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.imagefile)
        self.pixbuf_count += 1

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

        # Don't resize the image if in the middle of a fade -- too slow!
        # if not self.pixbuf or not self.d_alpha or self.alpha == 0:
        if self.imagefile and not self.pixbuf:
            try:
                self.setup_image()
            except gi.repository.GLib.Error as e:
                print("Couldn't open image", newcontent, ":", e)
                self.content = self.imagefile
                return self.draw_text(ctx)

        imgW = self.pixbuf.get_width()
        imgH = self.pixbuf.get_height()
        x = (self.width - imgW) / 2
        y = (self.height - imgH) / 2

        self.clear(ctx)
        Gdk.cairo_set_source_pixbuf(ctx, self.pixbuf, x, y)
        ctx.paint_with_alpha(self.alpha)

    def parse_colors(self, c):
        try:
            if len(c) == 3:
                return c
        except:
            pass

        try:
            if c.startswith('('):
                blah
            if c.startswith('#'):
                blah
            gdk_parse_blah(c)
        except:
            pass

    def parse_colors(self, colors):
        try:
            fg, bg = colors

        except TypeError:
            try:
                fg, bg = colors.split(':')
            except (AttributeError, ValueError):
                raise RuntimeError("Don't know how to unpack colors:"
                                   + str(colors))

        self.background_color = parse_color(bg)
        self.text_color = parse_color(fg)

    def clear(self, ctx):
        """Clear the screen.
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

    def fade_cb(self):

        # Adjust fade
        self.alpha += self.d_alpha
        if self.alpha <= 0:
            self.alpha = 0
            self.d_alpha = FADE_FRAC

            # Fade out just finished, time to choose a new quote
            self.new_quote()

        elif self.alpha >= 1:
            # Fading finished
            self.alpha = 1
            self.d_alpha = 0

        self.content_area.queue_draw()

        if self.d_alpha:
            return True

        return False

    def key_press(self, widget, event):
        """Handle a key press event anywhere in the window"""

        if event.keyval == Gdk.KEY_q:
            Gtk.main_quit()
            return

        return False


class KioskWindow(AutoSizerWindow):
    def __init__(self, fullscreen=False, fadetime=2,
                 fontname="Serif Italic",
                 border_size=40, timeout=30):
        super().__init__(fullscreen=fullscreen,
                         fadetime=fadetime,
                         fontname=fontname,
                         border_size=border_size)
        self.timeout = timeout

        # quote_list can be a mixture of quotes and filenames
        self.quote_list = []

        GLib.timeout_add(self.timeout * 1000, self.timeout_cb)

    def new_quote(self):
        choice = random.choice(self.quote_list)
        # print("*** New choice", choice)

        self.set_content(choice)

        self.content_area.queue_draw()

    def add_content(self, newcontent):
        """Set the quotes that will be displayed.
           newcontent is a list of strings, quotes or filenames or both.
        """
        self.quote_list += newcontent

        self.new_quote()

    def timeout_cb(self):
        """The main timeout routine, called to change quotes.
        """
        # If fades are enabled, start one.
        # fade_cb will call new_quote() when the fade out is finished.
        if self.fadefrac:
            self.d_alpha = -self.fadefrac
            GLib.timeout_add(self.fademillis, self.fade_cb)

        # If no fades, pick a new quote immediately.
        else:
            self.new_quote()

        # Returning True keeps the timeout in effect; no need to set a new one.
        return True


if __name__ == "__main__":
    import argparse
    import sys

    def parse_colors(s):
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--fullscreen", dest="fullscreen",
                        action="store_true", default=False,
                        help="Run fullscreen regardless of screen size")
    parser.add_argument('-t', '--time', action="store",
                        dest="time", type=int, default=30,
                        help='Time in seconds to pause between quotes')
    parser.add_argument('-F', '--fadetime', action="store",
                        dest="fadetime", type=float, default=2.,
                        help='Fade time in seconds (0 = no fade)')
    parser.add_argument('-fn', '--fontname', action="store",
                        dest="fontname", default='Serif',
                        help='Font name')
    parser.add_argument('--colors', action="store",
                        dest="colors", default='yellow:black',
                        help='Colors, foreground:background')
    parser.add_argument('quotes', nargs='+', help="Quotes, or files of quotes")
    args = parser.parse_args(sys.argv[1:])

    win = KioskWindow(fullscreen=args.fullscreen, timeout=args.time,
                      fadetime=args.fadetime, fontname=args.fontname)

    win.add_content(args.quotes)

    win.show_window()
    Gtk.main()

