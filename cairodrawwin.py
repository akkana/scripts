#!/usr/bin/env python3

# A Cairo window with a drawing area, suitable for inheriting from.

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
import cairo
from gi.repository import Pango
from gi.repository import PangoCairo

import argparse
import sys


class CairoDrawWindow(Gtk.Window):
    def __init__(self, message):
        super(CairoDrawWindow, self).__init__()

        self.message = message

        self.drawing_area = Gtk.DrawingArea()
        self.width = 1024
        self.height = 768
        self.set_default_size(self.width, self.height)

        self.add(self.drawing_area)

        self.drawing_area.connect('draw', self.draw)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key_press)

        self.show_all()

    def draw(self, widget, ctx):
        print("Draw")
        self.width, self.height = self.get_size()
        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()

        ctx.set_source_rgb(1, 1, 0)
        ctx.set_line_width(4)
        ctx.move_to(25, 25)
        ctx.line_to(self.width/2, self.height-10)
        ctx.line_to(self.width-25, 25)
        ctx.stroke()

        textcolor = self.bg_color = Gdk.color_parse('cyan')
        ctx.set_source_rgb(textcolor.red, textcolor.green, textcolor.blue)
        self.draw_string(self.message, ctx, self.width/2, self.height/2,
                         offsets=(0, 0))

    def draw_string(self, label, ctx, x, y, fontname="Serif Italic Bold 30",
                    offsets=None):
        """Draw a string at the specified point.
           offsets is an optional tuple specifying where the string will
           be drawn relative to the coordinates passed in;
           for instance, if offsets are (-1, -1) the string will be
           drawn with the bottom right edge at the given x, y.
        """

        layout = PangoCairo.create_layout(ctx)
        desc = Pango.font_description_from_string(fontname)
        layout.set_font_description(desc)
        layout.set_text(label, -1)

        if offsets:
            width, height = layout.get_pixel_size()

            if offsets[0] == 0:
                x -= int(width/2)
            elif offsets[0] != 1:
                x += int(width * offsets[0])
            if offsets[1] != 1:
                y += int(height * offsets[1] - height/2)

        ctx.move_to(x, y)
        PangoCairo.show_layout (ctx, layout)
        # ctx.show_text(label)

    def key_press(self, widget, event):
        """Handle a key press event anywhere in the window"""
        # Note: to handle just printables with no modifier keys,
        # use e.g. if event.string == "q"

        if event.keyval == Gdk.KEY_q:
            return Gtk.main_quit()

        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Cairo drawing window")
    parser.add_argument('-c', "--check", dest="check", default=False,
                        action="store_true", help="Check all the Things")
    parser.add_argument('message', nargs='*', default='Hello, world',
                        help="Message to draw")
    args = parser.parse_args(sys.argv[1:])

    win = CairoDrawWindow(' '.join(args.message))

    Gtk.main()


