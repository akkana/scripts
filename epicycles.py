#!/usr/bin/env python3

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
from pprint import pprint

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

planet_color_names = [ 'yellow', 'white', 'red', 'cyan', 'violet',
                       'green', 'blue', 'purple' ]

def color_to_triplet(c):
    return c.red, c.green, c.blue
    return c.red / 65535, c.green / 65535, c.blue / 65535

class EclipticPoleWindow(Gtk.Window):
    def __init__(self, auscale, timestep, time_increment=5, start_time=None):
        """time_increment is in days.
           start_time is a an ephem.Date object.
        """
        super(EclipticPoleWindow, self).__init__()

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
        # self.drawing_area.connect('configure-event', self.on_configure)
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

        ctx.set_source_rgb(self.bg_color.red, self.bg_color.green,
                           self.bg_color.blue)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()

        ctx.set_line_width(self.line_width)
        for i, path in enumerate(self.planet_paths):
            if not path:
                continue
            ctx.set_source_rgb(*color_to_triplet(self.planet_colors[i]))
            ctx.move_to(*path[0])
            for x, y in path[1:]:
                ctx.line_to(x, y)

            ctx.stroke()

    def idle_cb(self):
        """Calculate and draw the next position of each planet.
        """
        # self.time += ephem.date(self.time + self.time_increment)
        self.time += self.time_increment

        ctx = self.drawing_area.get_window().cairo_create()

        for i, p in enumerate(planets):
            halfwidth = self.width/2.
            halfheight = self.height/2.

            p.compute(self.time)
            ra = p.ra
            dist = p.earth_distance

            dist_scale = halfheight * dist / self.auscale
            x = dist_scale * math.cos(ra) + halfwidth
            y = dist_scale * math.sin(ra) + halfheight
            if self.planet_paths[i]:
                ctx.set_source_rgb(*color_to_triplet(self.planet_colors[i]))
                ctx.new_path()
                ctx.move_to(*self.planet_paths[i][-1])
                ctx.line_to(x, y)
                ctx.stroke()
                ctx.close_path()

            self.planet_paths[i].append((x, y))

        # Returning True reschedules the timeout.
        return self.stepping

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

