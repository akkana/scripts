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

from tkinter import Tk, Canvas, mainloop

import math
import argparse
import sys
from datetime import datetime

planets = [
    { "name": "Earth", "obj": ephem.Sun(), "colorname": "blue",
      "path": [], "xypath": [],
      "line": None, "disk": None },
    { "name": "Mars", "obj": ephem.Mars(), "colorname": "red",
      "path": [], "xypath": [], "oppositions": [],
      "line": None, "disk": None },
]

# oppositions will include date, earth hlon, earth dist, mars hlon, mars dist
oppositions = []

table_header = "%-20s %10s %10s" % ("Date", "Distance", "Size")
table_format = "%-20s %10.3f %10.2f"


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


class OrbitViewWindow():
    def __init__(self, auscale, timestep, time_increment=1, start_time=None):
        """time_increment is in days.
           start_time is a an ephem.Date object.
        """
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

        self.linewidth = 3

        self.width = 1024
        self.height = 768

        self.halfwidth = self.width/2.
        self.halfheight = self.height/2.
        self.dist_scale = self.halfheight / self.auscale

        tkmaster =  Tk()
        self.canvas = Canvas(tkmaster, bg="black",
                             width=self.width, height=self.height)
        self.canvas.pack()

        tkmaster.bind("<KeyPress-q>", sys.exit)

        print(table_header)

        # Schedule the first draw
        self.step_draw()

    def step_draw(self):
        """Calculate and draw the next position of each planet.
        """
        # Adding a float to ephem.Date turns it into a float.
        # You can get back an ephem.Date with: ephem.Date(self.time).
        self.time += self.time_increment

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

            xn, yn = self.planet_x_y(hlon, sundist)
            radius = 10
            p["xypath"].append(int(xn))
            p["xypath"].append(int(yn))
            if p["line"]:
                self.canvas.coords(p["line"], p["xypath"])
                self.canvas.coords(p["disk"], xn-radius, yn-radius,
                                   xn+radius, yn+radius)

            else:
                p["line"] = self.canvas.create_line(xn, yn, xn, yn,
                                                    width=self.linewidth,
                                                    fill=p["colorname"])
                p["disk"] = self.canvas.create_oval(xn-radius, yn-radius,
                                                    xn+radius, yn+radius,
                                                    fill=p["colorname"])

            p["path"].append((hlon, sundist, earthdist, size))

        if self.stepping:
            self.canvas.after(self.timestep, self.step_draw)

    def planet_x_y(self, hlon, dist):
        return (dist * self.dist_scale * math.cos(hlon) + self.halfwidth,
                dist * self.dist_scale * math.sin(hlon) + self.halfheight)


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

    mainloop()

