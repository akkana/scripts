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

from tkinter import Tk, Canvas, PhotoImage, mainloop, LEFT

import math
import argparse
import sys, os
from datetime import datetime

ICONDIR = os.path.expanduser("~/Docs/Preso/mars/pix/")

earth = { "name": "Earth", "obj": ephem.Sun(), "color": "#08f",
          "path": [], "xypath": [],
          "line": None, "disk": None,
          "imgname": os.path.join(ICONDIR, "tinyearth.png") }

mars = { "name": "Mars", "obj": ephem.Mars(), "color": "#f80",
         "path": [], "xypath": [], "oppositions": [],
         "line": None, "disk": None,
         "imgname": os.path.join(ICONDIR, "tinymars.png") }

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
        tkmaster.title("Mars Oppositions")
        self.canvas = Canvas(tkmaster, bg="black",
                             width=self.width, height=self.height)
        # Start with just the Sun
        try:
            self.sunimg = PhotoImage(file=os.path.join(ICONDIR, "tinysun.png"))
            self.canvas.create_image(self.width/2, self.height/2,
                                     image=self.sunimg)
        except:
            sunrad = 20
            self.canvas.create_oval(self.width/2 - sunrad,
                                    self.height/2 - sunrad,
                                    self.width/2 + sunrad,
                                    self.height/2 + sunrad,
                                    fill="yellow")

        self.canvas.pack()

        # Canvas requires that the app save a reference to PhotoImages:
        # the canvas doesn't keep the references.
        try:
            earth["tinyimg"] = PhotoImage(file=earth["imgname"])
        except:
            earth["tinyimg"] = None
        try:
            mars["tinyimg"] = PhotoImage(file=mars["imgname"])
        except:
            mars["tinyimg"] = None

        tkmaster.bind("<KeyPress-q>", sys.exit)
        tkmaster.bind("<KeyPress-space>", self.toggle_stepping)

        print(table_header)

        # Schedule the first draw
        self.step_draw()

    def toggle_stepping(self, key):
        self.stepping = not self.stepping

    def step_draw(self):
        """Calculate and draw the next position of each planet.
        """
        # If we don't call step_draw at all, we'll never get further key events
        # that could restart the animation. So just step at a much slower pace.
        if not self.stepping:
            self.canvas.after(500, self.step_draw)
            return

        # Adding a float to ephem.Date turns it into a float.
        # You can get back an ephem.Date with: ephem.Date(self.time).
        self.time += self.time_increment

        for p in (earth, mars):
            p["obj"].compute(self.time)

            # ephem treats Earth specially, what a hassle!
            # There is no ephem.Earth body; ephem.Sun gives the Earth's
            # hlon as hlon, but I guess we need to use earth_distance.
            oppy = False
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
                    oppy = True
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

            xn, yn = self.planet_x_y(hlon, sundist)
            radius = 10

            if oppy:
                # Create outline circles for Mars and Earth at opposition.
                # xn, yn should be Mars since Earth was done first.
                # Create the open circle at the bottom of the stacking order.
                # There may be a way to do this by passing in tags,
                # but I can't find any documentation on tags.
                self.canvas.tag_lower(
                    self.canvas.create_oval(xn-radius, yn-radius,
                                            xn+radius, yn+radius,
                                            outline=p["color"], width=3)
                )

                earthx = earth["xypath"][-2]
                earthy = earth["xypath"][-1]
                self.canvas.tag_lower(
                    self.canvas.create_oval(earthx-radius, earthy-radius,
                                            earthx+radius, earthy+radius,
                                            outline=earth["color"], width=3)
                )

                localtz = datetime.now().astimezone().tzinfo
                oppdate = ephem.to_timezone(self.opp_date, localtz)
                opp_str = oppdate.strftime("%Y-%m-%d") + \
                    '\n%.3f AU\n%.1f"' % (earthdist, size)
                if xn < self.width/2:
                    if yn < self.height / 2:
                        anchor = "se"
                    else:
                        anchor = "ne"
                    xtxt = xn - radius
                else:
                    if yn < self.height / 2:
                        anchor = "sw"
                    else:
                        anchor = "nw"
                    xtxt = xn + radius
                ytxt = yn

                txtobj = self.canvas.create_text(xtxt, ytxt,
                                                 fill="white", justify=LEFT,
                                                 font=('sans', 14, 'bold'),
                                                 anchor=anchor,
                                                 text=opp_str)
                # Make sure it's not offscreen
                xt1, yt1, xt2, yt2 = self.canvas.bbox(txtobj)
                if xt1 < 0:
                    xtxt -= xt1
                elif xt2 > self.width:
                    xtxt -= (xt2 - self.width)
                if yt1 < 0:
                    ytxt -= yt1
                elif yt2 > self.height:
                     ytxt -= yt2 - self.height
                self.canvas.coords(txtobj, xtxt, ytxt)

                # Done with this opposition: find the next one.
                self.opp_date, self.closest_date \
                    = find_next_opposition(self.time + 500)

            p["xypath"].append(int(xn))
            p["xypath"].append(int(yn))
            if p["line"]:
                self.canvas.coords(p["line"], p["xypath"])
                if p["tinyimg"]:
                    self.canvas.coords(p["disk"], xn, yn)
                else:
                    self.canvas.coords(p["disk"], xn-radius, yn-radius,
                                       xn+radius, yn+radius)

            else:
                p["line"] = self.canvas.create_line(xn, yn, xn, yn,
                                                    width=self.linewidth,
                                                    fill=p["color"])
                # Use images if there are any, else circles
                if p["tinyimg"]:
                    p["disk"] = self.canvas.create_image(xn-radius, yn-radius,
                                                         image=p["tinyimg"])
                else:
                    p["disk"] = self.canvas.create_oval(xn-radius, yn-radius,
                                                        xn+radius, yn+radius,
                                                        fill=p["color"])

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
    parser.add_argument('-a', "--au", dest="auscale", type=float, default=1.7,
                        action="store",
                        help="""Scale of the window in astronomical units.
Default is 11, which shows Saturn.
2.6 shows Mars, 30 shows some of Pluto, 50 shows all of Pluto.""")
    parser.add_argument('-t', "--timestep", dest="timestep",
                        type=int, default=30,
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

