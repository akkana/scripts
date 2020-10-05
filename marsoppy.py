#!/usr/bin/env python3

# Plot all the planets' orbits, as viewed from a point that
# floats above the Earth's north ecliptic pole and moves with
# the Earth, to demonstrate phenomena like epicycles and the
# Venus pentagram. Idea from Galen Gisler's planetarium show.
#
# Copyright 2020 by Akkana Peck: Share and enjoy under the GPLv2 or later.

# Weird GLib bug: GLib.timeout_add takes an integer number
# of milliseconds, but if you pass it a float, it sets the timeout
# but then doesn't call draw() automatically after configure(),
# resulting in a transparent window since the black background
# doesn't get drawn. I guess it's some mysterious GTK/Cairo bug.
# Of course I could require an integer timeout when parsing arguments,
# but it's such an amusingly weird bug that I've left it as a float.

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
    { "name": "Earth", "obj": ephem.Sun(), "colorname": "blue",
      "path": [] },
    { "name": "Mars", "obj": ephem.Mars(), "colorname": "red",
      "path": [], "oppositions": [] },
]

# oppositions will include date, earth hlon, earth dist, mars hlon, mars dist
oppositions = []

table_header = "%-20s %10s %10s" % ("Date", "Distance", "Size")
table_format = "%-20s %10.3f %10.2f"

# Cairo drawing wants color components to go from 0 to 1; GTK uses 0 to 65535.
# The good thing about standards is that there are so many of them.
def color_to_triplet(c):
    return c.red / 65535, c.green / 65535, c.blue / 65535


def find_next_opposition(start_time):
    """Find oppsition and time of closest approach for the given time range.
       Input is the start time, either in ephem.Date or float julian.
       Output is two ephem.Dates: opposition, closest approach
    """
    t = start_time
    timedelta = ephem.hour * 6
    mars = ephem.Mars()
    sun = ephem.Sun()
    min_dist = 20
    oppy_date = None
    closest_date = None
    last_dlon = None

    # Loop til we've found opposition, plus 15 days.
    # Opposition is when dlon changes sign and is very small.
    while not oppy_date or t - oppy_date < 15:
        mars.compute(t)
        sun.compute(t)
        dlon = mars.hlon - sun.hlon

        # Does dlon have the opposite sign from last_dlon?
        if last_dlon and abs(dlon) < .1 and \
           (dlon == 0 or (dlon < 0) != (last_dlon < 0)):
            oppy_date = t
        if mars.earth_distance < min_dist:
            closest_date = t
            min_dist = mars.earth_distance

        if oppy_date and closest_date:
            return ephem.Date(oppy_date), ephem.Date(closest_date)

        last_dlon = dlon
        t += timedelta


class OrbitViewWindow(Gtk.Window):
    def __init__(self, auscale, timestep, time_increment=1, start_time=None):
        """time_increment is in days.
           start_time is a an ephem.Date object.
        """
        super().__init__()

        self.auscale = auscale
        self.timestep = timestep
        self.stepping = True

        self.year = 0

        if start_time:
            self.time = start_time
        else:
            self.time = ephem.Date(datetime.now()) - ephem.hour * 24 * 7
        print("Start time:", ephem.Date(self.time))

        self.opp_date, self.closest_date = find_next_opposition(self.time)
        # print("Next opposition:", self.opp_date)
        # print("Next closest:", self.closest_date)

        self.time_increment = ephem.hour * time_increment * 24

        # Paths for each planet. Must save the full path
        # since we might need to redraw if the window gets covered.
        self.planet_paths = [ [] for i in range(len(planets)) ]

        # Set up colors
        self.bg_color = Gdk.color_parse('black')
        for p in planets:
            p["color"] = Gdk.color_parse(p["colorname"])

        self.line_width = 3

        self.drawing_area = Gtk.DrawingArea()
        self.set_default_size(1024, 768)
        self.add(self.drawing_area)

        GLib.timeout_add(self.timestep, self.idle_cb)

        self.drawing_area.connect('draw', self.draw)
        self.drawing_area.connect('configure-event', self.configure)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key_press)

        # GLib.idle_add(self.idle_cb)

        self.show_all()

        print(table_header)

    def draw(self, widget, ctx):
        # print("Draw")

        if not ctx:
            print("Draw with no cairo context")
            ctx = widget.get_window().cairo_create()

        ctx.set_source_rgb(self.bg_color.red, self.bg_color.green,
                           self.bg_color.blue)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()

        # This makes no sense: specified line width has to be one less here
        # than it does in idle_cb to result in the same line width.
        ctx.set_line_width(self.line_width-1)
        for p in planets:
            if not p["path"]:
                continue

            ctx.set_source_rgb(*color_to_triplet(p["color"]))
            self.planet_segment(ctx, *p["path"][0], False)
            for ra, dist in p["path"][1:]:
                self.planet_segment(ctx, ra, dist, True)

            ctx.stroke()

    def idle_cb(self):
        """Calculate and draw the next position of each planet.
        """
        if not self.width:
            print("idle: skipping")
            return True

        # Adding a float to ephem.Date turns it into a float.
        # You can get back an ephem.Date with: ephem.Date(self.time).
        self.time += self.time_increment

        # year = ephem.Date(self.time).triple()[0]
        # if year > self.year:
        #     print(year)
        #     self.year = year

        ctx = self.drawing_area.get_window().cairo_create()

        for p in planets:
            p["obj"].compute(self.time)
            # ephem treats Earth specially, what a hassle!
            # There is no ephem.Earth body; ephem.Sun gives the Earth's
            # hlon as hlon, but I guess we need to use earth_distance.
            if p["name"] == "Earth":
                hlon = p["obj"].hlon
                sundist = p["obj"].earth_distance
                earthdist = 0
                size = 0
            else:
                hlon = p["obj"].hlon
                sundist = p["obj"].sun_distance
                earthdist = p["obj"].earth_distance
                size = p["obj"].size

                if abs(self.time - self.opp_date) <= .5:
                    if self.opp_date < self.closest_date:
                        print(table_format % (self.opp_date, earthdist, size),
                              "Opposition")
                        print(table_format % (self.closest_date,
                                              earthdist, size),
                              "Closest approach")
                    else:
                        print(table_format % (self.closest_date,
                                              earthdist, size),
                              "Closest approach")
                        print(table_format % (self.opp_date, earthdist, size),
                              "Opposition")

                    # Draw the planet
                    # ctx.set_operator(cairo.Operator.IN)
                    # ctx.arc(xn, yn, 10.0, 0, 2*math.pi);
                    # ctx.stroke()
                    # ctx.set_operator(cairo.Operator.OVER)

                    self.opp_date, self.closest_date \
                        = find_next_opposition(self.time + 2)

            if p["path"]:
                ctx.set_source_rgb(*color_to_triplet(p["color"]))
                ctx.new_path()

                # Move to end of last segment
                xl, yl = self.planet_x_y(p["path"][-1][0], p["path"][-1][1])
                ctx.move_to(xl, yl)

                # ... and draw to new position.
                xn, yn = self.planet_x_y(hlon, sundist)
                ctx.line_to(xn, yn)

                ctx.stroke()
                ctx.close_path()
                # print("Operator:", ctx.get_operator())

            p["path"].append((hlon, sundist, earthdist, size))

        # Returning True reschedules the timeout.
        return self.stepping

    def planet_x_y(self, hlon, dist):
        return (dist * self.dist_scale * math.cos(hlon) + self.halfwidth,
                dist * self.dist_scale * math.sin(hlon) + self.halfheight)

    def configure(self, widget, event):
        """Window size change: reset the scale factors."""
        # print("configure")
        self.width, self.height = self.get_size()
        self.halfwidth = self.width/2.
        self.halfheight = self.height/2.
        self.dist_scale = self.halfheight / self.auscale

        # self.draw(widget, None)

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


def print_table():
    """Super quickie hack to print out a table for the current opposition.
       Unrelated to any of the other code in this script.
       Ought to be generalized to take start and stop times, etc.
    """
    start_date = ephem.Date(datetime.now()) - ephem.hour*24*10
    end_date = start_date + ephem.hour*24*40
    opp_date, closest_date = find_next_opposition(start_date)
    print("Opposition:", opp_date)
    print("Closest approach:", closest_date)

    # Define "opposition season"
    d = opp_date - ephem.hour * 24 * 15
    end_date = opp_date + ephem.hour * 24 * 20

    mars = ephem.Mars()
    print(table_header)
    while d < start_date + 60:
        mars.compute(d)
        d += ephem.hour * 24
        if abs(d - opp_date) <= .5:
            print(table_format % (ephem.Date(d), mars.earth_distance,
                                  mars.size), "** OPPOSITION")
        elif abs(d - closest_date) <= .5:
            print(table_format % (ephem.Date(d), mars.earth_distance,
                                  mars.size), "** CLOSEST APPROACH")
        else:
            print(table_format % (ephem.Date(d), mars.earth_distance,
                                  mars.size))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""Draw planet orbits from the north ecliptic pole.

Key bindings:
  space   Start/stop animation
  q       quit""",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-a', "--au", dest="auscale", type=float, default=2.6,
                        action="store",
                        help="""Scale of the window in astronomical units.
Default is 11, which shows Saturn.
2.6 shows Mars, 30 shows some of Pluto, 50 shows all of Pluto.""")
    parser.add_argument('-t', "--timestep", dest="timestep",
                        type=float, default=30,
                        help="""Time step in milliseconds (default 30).
Controls how fast the orbits are drawn.""")
    parser.add_argument('-T', "--table", dest="table", action="store_true",
                        help="Forget all that graphic stuff and just "
                             "print a table of sizes around opposition")
    args = parser.parse_args(sys.argv[1:])

    if args.table:
        print_table()
        sys.exit(0)

    win = OrbitViewWindow(auscale=args.auscale, timestep=args.timestep)

    Gtk.main()

