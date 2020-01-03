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

import random

class ParagraphWindow(Gtk.Window):
    def __init__(self, width=1024, height=768, fullscreen=False,
                 border_size=40):
        super(ParagraphWindow, self).__init__()

        self.drawing_area = None

        self.width = width
        self.height = height
        self.use_fullscreen = fullscreen

        self.border_size = border_size

        self.background_color = (0, 0, 0)
        self.text_color = (1, 1, 0)

        self.text = "test 1 2 3"

    def show_window(self):
        self.drawing_area = Gtk.DrawingArea()
        if self.use_fullscreen:
            self.fullscreen()
        else:
            self.set_default_size(self.width, self.height)
        self.add(self.drawing_area)
        # self.connect("delete_event", Gtk.main_quit)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key_press)
        self.drawing_area.connect('draw', self.draw)
        self.show_all()

    def draw_paragraph(self, paragraph, ctx):
        """Draw the paragraph as large as can fit."""

        # Clear the page
        ctx.set_source_rgb(*self.background_color)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()
        ctx.set_source_rgb(*self.text_color)

        layout = PangoCairo.create_layout(ctx)
        layout.set_text(paragraph, -1)

        # For some reason pango width has to be 1024 times the width.
        # Why? Where does this 1024 come from?
        # No one explains this anywhere.
        # layout.set_width(self.width * self.get_allocation().width)
        layout.set_width(1024 * (self.width - self.border_size*2))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)

        fontsize = 100

        while fontsize:
            fontname = "Serif Italic %d" % fontsize
            desc = Pango.font_description_from_string(fontname)
            layout.set_font_description(desc)
            pxsize = layout.get_pixel_size()
            if pxsize.width < self.width - self.border_size*2 and \
               pxsize.height < self.height - self.border_size*2:
                break
            fontsize -= 1

        ctx.move_to(self.border_size, self.border_size)
        PangoCairo.show_layout (ctx, layout)
        # self.ctx.show_text(label)

    def draw(self, widget, ctx):
        """Draw everything: the analemma and all the labels.
           If background isn't passed, we'll default to
           self.background_color (opaque blue), but save_image()
           will pass in a transparent background.
        """
        self.width, self.height = self.get_size()
        self.draw_paragraph(self.text, ctx)

    def key_press(self, widget, event):
        """Handle a key press event anywhere in the window"""
        # Note: to handle just printables with no modifier keys,
        # use e.g. if event.string == "q"

        if event.keyval == Gdk.KEY_q:
            Gtk.main_quit()
            return
        if event.keyval == Gdk.KEY_s and \
           event.state & Gdk.ModifierType.CONTROL_MASK:
            obsname = self.observer.name.replace(' ', '-')
            self.save_image("Analemma-%s.png" % obsname, labels=False)
            self.save_image("Analemma-%s-labels.png" % obsname, labels=True)
            return True
        return False

class KioskWindow(ParagraphWindow):
    def __init__(self, width=1024, height=768, fullscreen=False,
                 border_size=40, timeout=5):
        super(KioskWindow, self).__init__(width, height,
                                          fullscreen, border_size)
        self.timeout = timeout

        self.texts = None

        GLib.timeout_add(self.timeout * 1000, self.timeout_cb)

    def timeout_cb(self):
        print("blip")
        if self.texts:
            self.text = random.choice(self.texts)
            self.drawing_area.queue_draw()

        GLib.timeout_add(self.timeout * 1000, self.timeout_cb)


if __name__ == "__main__":
    def Usage():
        progname = os.path.basename(sys.argv[0])
        print("""Usage: %s [cityname [sun|moon]]
       %s lat lon [sun|moon]""" % (progname, progname))
        sys.exit(0)

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '-f':
        win = KioskWindow(fullscreen=True)
    else:
        win = KioskWindow(width=1024, height=768)

    win.texts = ["To be, or not to be--that is the question: Whether 'tis nobler in the mind to suffer The slings and arrows of outrageous fortune Or to take arms against a sea of troubles And by opposing end them. To die, to sleep-- No more--and by a sleep to say we end The heartache, and the thousand natural shocks That flesh is heir to. 'Tis a consummation Devoutly to be wished. To die, to sleep-- To sleep--perchance to dream: ay, there's the rub, For in that sleep of death what dreams may come When we have shuffled off this mortal coil, Must give us pause. There's the respect That makes calamity of so long life.",
                 "The quick red fox jumped over the lazy dog",
                 "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
                 ]

    win.show_window()
    Gtk.main()

