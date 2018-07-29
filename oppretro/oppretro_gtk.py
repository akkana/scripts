#!/usr/bin/env python3

# oppretro will be imported from main, depending on commandline arguments.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gdk

import cairo
from gi.repository import Pango
from gi.repository import PangoCairo

import math
import sys

# Import one or the other version of oppretro depending on
# commandline arguments. Alas, this can't be done in __main__,
# because that's executed after the class definitions that
# depend on the oppretro.OppRetro class.
if len(sys.argv) > 1 and sys.argv[1] == '-a':
    print("Using AstroPy")
    import oppretro_astropy as oppretro
else:
    print("Using PyEphem")
    import oppretro_ephem as oppretro

class OppRetroWindow(Gtk.Window, oppretro.OppRetro):
    def __init__(self, location, background=None):
        # Python doesn't let you use super() with multiple base
        # classes whose constructors take different argument lists.
        oppretro.OppRetro.__init__(self, location)
        Gtk.Window.__init__(self)

        if background:
            self.background_color = background
        else:
            self.background_color = (0, 0, .3, 1)

        self.planet_color = (1, 1, .5, 1)

        self.save_all_points = True

    def show_window(self):
        self.drawing_area = Gtk.DrawingArea()
        self.set_default_size(800, 600)
        self.add(self.drawing_area)
        # self.connect("delete_event", Gtk.main_quit)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key_press)
        self.drawing_area.connect('draw', self.draw)
        self.show_all()
        Gtk.main()

    def find_opp_and_retro(self, start_date):
        oppretro.OppRetro.find_opp_and_retro(self, start_date)

        self.draw()

    def draw(self, widget=None, ctx=None, background=None, labels=True):
        '''Draw everything.
           If background isn't passed, we'll default to
           self.background_color (opaque blue), but save_image()
           will pass in a transparent background.
        '''
        if ctx:
            self.ctx = ctx
        if not ctx:
            # print("Too early, no drawing context yet")
            return

        self.width, self.height = self.get_size()

        # Draw the background.
        if not background:
            background = self.background_color
        ctx.set_source_rgba(*background)
        self.draw_rectangle(0, 0, self.width, self.height)

        # Calculate bounds
        self.min_RA = math.pi * 2.
        max_RA = 0.
        self.min_dec = math.pi / 2.
        max_dec = -self.min_dec
        # print("coords:", self.planettrack)
        for point in self.planettrack:
            self.min_RA = min(self.min_RA, point[oppretro.IRA])
            max_RA = max(max_RA, point[oppretro.IRA])
            self.min_dec = min(self.min_dec, point[oppretro.IDEC])
            max_dec = max(max_dec, point[oppretro.IDEC])

        # print()
        # print("Bounds:", self.angle_to_hours(self.min_RA),
        #       self.angle_to_hours(max_RA),
        #       self.angle_to_degrees(self.min_dec),
        #       self.angle_to_degrees(max_dec))

        spacefactor = .2
        self.RA_scale = float(self.width) / (max_RA - self.min_RA)
        self.dec_scale = float(self.height) / (max_dec - self.min_dec)

        # Make the bounds a little more roomy
        self.min_RA -= (max_RA - self.min_RA) * spacefactor / 2.
        self.RA_scale /= (1. + spacefactor)
        self.min_dec -= (max_dec - self.min_dec) * spacefactor / 2.
        self.dec_scale /= (1. + spacefactor)

        # Now do some plotting.
        ctx.set_source_rgba(*self.planet_color)

        for point in self.planettrack:
            # print("dec:", point[oppretro.IDEC] -self. min_dec, '*', dec_scale)
            x = self.RA2X(point[oppretro.IRA])
            y = self.dec2Y(point[oppretro.IDEC])
            # print("draw_dot", x, y)
            if point[oppretro.IFLAGS]:
                self.draw_string(point[oppretro.IDATE].strftime('%Y-%m-%d')
                                 + " " +
                                 self.flags_to_string(point[oppretro.IFLAGS]),
                                 x, y, offsets=(1, 1), xspacing=10, yspacing=0)
                self.draw_dot(x, y, 6)
            else:
                self.draw_dot(x, y, 2)

    def RA2X(self, ra):
        return self.width - (ra - self.min_RA) * self.RA_scale

    def dec2Y(self, dec):
        return self.height - (dec - self.min_dec) * self.dec_scale

    def draw_dot(self, x, y, dotsize):
        self.ctx.rectangle(x, y, dotsize, dotsize)
        self.ctx.fill()

    def draw_rectangle(self, x, y, width, height):
        self.ctx.rectangle(x, y, width, height)
        self.ctx.fill()

    def draw_string(self, label, x, y, offsets=None, xspacing=4, yspacing=4):
        '''Draw a string at the specified point.
           offsets is an optional tuple specifying where the string will
           be drawn relative to the coordinates passed in;
           for instance, if offsets are (-1, -1) the string will be
           drawn with the bottom right edge at the given x, y.
        '''
        fontname = "Sans Italic 12"

        layout = PangoCairo.create_layout(self.ctx)
        desc = Pango.font_description_from_string(fontname)
        layout.set_font_description( desc)
        layout.set_text(label, -1)

        if offsets:
            width, height = layout.get_pixel_size()
            # # pango draws text with the upper left corner at x, y.
            # # So that's an offset of (1, 1). Adjust if offsets are different.
            # # XXX Cairo may do things differently.
            # xbearing, ybearing, width, height, xadvance, yadvance = \
            #                                   self.ctx.text_extents(label)

            if offsets[0] == 0:
                x -= int(width/2)
            elif offsets[0] != 1:
                x += int(width * offsets[0])
                if offsets[0] < 1:
                    xspacing = -xspacing

            # Weirdly, height is quite a bit taller than the text height
            height *= .55
            if offsets[1] == 0:
                y -= int(height/2)
            else:
                y -= int(height * (offsets[1] + .5))
                if offsets[1] < 1:
                    yspacing = -yspacing

        # Will the text be off the screen?
        if x < 0:
            x += width
            xspacing = -xspacing
        elif x + width > self.width:
            x -= width
            xspacing = -xspacing
        if y < 0:
            y += height
            yspacing = -yspacing
        elif y + height > self.height:
            y -= height
            yspacing = -yspacing

        self.ctx.move_to(x + xspacing, y + yspacing)
        PangoCairo.show_layout (self.ctx, layout)
        # self.ctx.show_text(label)

    def key_press(self, widget, event):
        '''Handle a key press event anywhere in the window'''
        # Note: to handle just printables with no modifier keys,
        # use e.g. if event.string == "q"

        if event.keyval == Gdk.KEY_q:
            Gtk.main_quit()
            return

        return False


if __name__ == '__main__':
    start_date = '2018-05-01 00:00:00'

    cityname = "Los Alamos, NM"
    # cityname = "Prague"

    oppy = OppRetroWindow(cityname)
    oppy.find_opp_and_retro(start_date)
    oppy.show_window()


