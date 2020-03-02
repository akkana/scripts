#!/usr/bin/env python3

# Plot all the planets' orbits, as viewed from a point that
# floats above the Earth's north ecliptic pole and moves with
# the Earth, to demonstrate phenomena like epicycles and the
# Venus pentagram. Idea from Galen Gisler's planetarium show.
#
# Copyright 2020 by Akkana Peck: Share and enjoy under the GPLv2 or later.

import ephem

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
import cairo

import math
import argparse
import sys
from datetime import datetime

planets = [
    ephem.Mercury(),
    ephem.Venus(),
    ephem.Mars(),
    ephem.Jupiter(),
    ephem.Saturn(),
    ephem.Uranus(),
    ephem.Neptune(),
    ephem.Pluto()
    ]

# For some reason, Gdk's "green" is not the 0 255   0 from rgb.txt, but
# comes out (red=0, green=32896, blue=0). But it parses green1 correctly.
planet_color_names = [ 'yellow', 'white', 'red', 'cyan', 'violet',
                       'green1', 'blue', 'purple' ]

# Cairo drawing wants color components to go from 0 to 1; GTK uses 0 to 65535.
# The good thing about standards is that there are so many of them.
def color_to_triplet(c):
    return c.red / 65535, c.green / 65535, c.blue / 65535

class EclipticPoleWindow(Gtk.Window):
    def __init__(self, auscale, timestep, time_increment=5, start_time=None):
        """time_increment is in days.
           start_time is a an ephem.Date object.
        """
        super().__init__()

        self.auscale = auscale
        self.timestep = timestep
        self.stepping = True

        if start_time:
            self.time = start_time
        else:
            self.time = ephem.Date(datetime.now())

        self.time_increment = ephem.hour * time_increment * 24

        # Paths for each planet. Must save the full path
        # since we might need to redraw if the window gets covered.
        self.planet_paths = [ [] for i in range(len(planets)) ]

        # Set up colors
        self.bg_color = Gdk.color_parse('black')
        self.planet_colors = [ Gdk.color_parse(c) for c in planet_color_names ]

        self.line_width = 3

        self.drawing_area = Gtk.DrawingArea()
        self.width = 1024
        self.height = 768
        self.set_default_size(self.width, self.height)
        self.add(self.drawing_area)

        GLib.timeout_add(self.timestep, self.idle_cb)

        self.drawing_area.connect('draw', self.draw)
        self.drawing_area.connect('configure-event', self.configure)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key_press)

        # GLib.idle_add(self.idle_cb)

        self.show_all()

    def draw(self, widget, ctx):
        # print("Draw")
        self.width, self.height = self.get_size()

        # There is no easy way to get a DrawingArea's context,
        # besides getting it in draw(), but idle_cb needs it
        # to draw incrementally. So save it here.
        self.ctx = ctx

        self.configure(None, None)

        ctx.set_source_rgb(self.bg_color.red, self.bg_color.green,
                           self.bg_color.blue)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()

        # This makes no sense: specified line width has to be one less here
        # than it does in idle_cb to result in the same line width.
        ctx.set_line_width(self.line_width-1)
        for i, path in enumerate(self.planet_paths):
            if not path:
                continue
            ctx.set_source_rgb(*color_to_triplet(self.planet_colors[i]))
            self.planet_segment(ctx, *path[0], False)
            for pair in path[1:]:
                self.planet_segment(ctx, *pair, True)

            ctx.stroke()

    def idle_cb(self):
        """Calculate and draw the next position of each planet.
        """
        # self.time += ephem.date(self.time + self.time_increment)
        self.time += self.time_increment

        ctx = self.drawing_area.get_window().cairo_create()

        for i, p in enumerate(planets):

            p.compute(self.time)
            ra = p.ra
            dist = p.earth_distance

            if self.planet_paths[i]:
                ctx.set_source_rgb(*color_to_triplet(self.planet_colors[i]))
                ctx.new_path()

                self.planet_segment(ctx, *self.planet_paths[i][-1], False)
                self.planet_segment(ctx, ra, dist, True)

                ctx.stroke()
                ctx.close_path()

            self.planet_paths[i].append((ra, dist))

        # Returning True reschedules the timeout.
        return self.stepping

    def planet_segment(self, ctx, ra, dist, drawp):
        """Draw (if drawp) or move to the appropriate place on the screen
           for the given ra and dist coordinates.
        """
        x = dist * self.dist_scale * math.cos(ra) + self.halfwidth
        y = dist * self.dist_scale * math.sin(ra) + self.halfheight
        if drawp:
            ctx.line_to(x, y)
        else:
            ctx.move_to(x, y)

    def configure(self, widget, event):
        """Window size change: reset the scale factors."""
        self.halfwidth = self.width/2.
        self.halfheight = self.height/2.
        self.dist_scale = self.halfheight / self.auscale

    def key_press(self, widget, event):
        """Handle a key press event anywhere in the window"""
        # Note: to handle just printables with no modifier keys,
        # use e.g. if event.string == "q"

        if event.keyval == Gdk.KEY_q:
            return Gtk.main_quit()

        if event.keyval == Gdk.KEY_space:
            self.stepping = not self.stepping
            if self.stepping:
                GLib.timeout_add(self.timestep, self.idle_cb)

        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""Draw planet orbits from the north ecliptic pole.

Key bindings:
  space   Start/stop animation
  q       quit""",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-a', "--au", dest="auscale", type=float, default=11,
                        action="store",
                        help="""Scale of the window in astronomical units.
Default is 11, which shows Saturn.
2.6 shows Mars, 30 shows Pluto.""")
    parser.add_argument('-t', "--timestep", dest="timestep",
                        type=float, default=30,
                        help="""Time step in milliseconds (default 30).
Controls how fast the orbits are drawn.""")
    args = parser.parse_args(sys.argv[1:])

    win = EclipticPoleWindow(auscale=args.auscale, timestep=args.timestep)

    Gtk.main()

