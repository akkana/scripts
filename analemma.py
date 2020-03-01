#! /usr/bin/env python3

# Display an analemma for a specified location and time.
# Copyright 2011,2017 by Akkana Peck: share and enjoy under the GPL v2 or later.

# If you see:
#   Couldn't find foreign struct converter for 'cairo.Context'
# it probably means you need python3-gi-cairo.

import ephem
from ephem import cities
import sys
import os
import math

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import cairo
from gi.repository import Pango
from gi.repository import PangoCairo

class AnalemmaWindow(Gtk.Window):
    def __init__(self, observer, year, lunar=False, background=None):
        super().__init__()

        self.observer = observer
        print("AnalemmaWindow: observer at %.1f %.1f" % (observer.lat,
                                                         observer.lon))
        self.year = year
        self.lunar = lunar

        self.special_dates = None
        self.drawing_area = None

        self.width = 0
        self.height = 0
        # Even if we're actually showing the moon, call the object self.sun.
        if self.lunar:
            self.sun = ephem.Moon()
        else:
            self.sun = ephem.Sun()
        self.sinusoidal = False

        self.sun_color = (1, 1, 0)
        self.backside_color = (1, .7, 0)
        self.text_color = (1, 1, 0)
        if background:
            self.background_color = background
        else:
            self.background_color = (0, 0, .6, 1)
        self.special_dot_size = 5

    def draw_sun_position(self, date):
        """Draw a sun at the appropriate position for date.
           date can be a string like "2018/8/9 12:00"
           which is the format pyephem expects,
           or an EphemDate.
        """
        if not self.drawing_area:
            print("no drawing area")
            return

        if type(date) is ephem.Date:
            self.observer.date = date
        else:
            self.observer.date = self.local_to_gmt(date, reverse=True)

        self.sun.compute(self.observer)

        # Y scale is 90 degrees (PI/2), horizon to zenith:
        # y = self.height - int(float(self.sun.alt) * self.height / math.pi * 2)

        # So make X scale 90 degrees too, centered around due south.
        # Want az = PI to come out at x = width/2,
        # az = PI/2 to be 0, 3*PI/2 = width.
        # x = int(float(self.sun.az) * self.width / math.pi * 2 - self.width / 2) % self.width

        self.project_and_draw(self.sun.az, self.sun.alt, 4)

    def calc_special_dates(self):
        """Earlist and latest rising and setting times,
           and longest/shortest day.
        """
        if self.special_dates:
            # Already done, nothing more to do.
            return

        self.special_dates = {
            'earliest sunrise': 24,
            'latest sunrise'  :  0,
            'earliest sunset' : 24,
            'latest sunset'   :  0,
            'longest day len' :  0,
            'shortest day len': 24
        }

        # Start just after midnight on New Year's Day.
        dt = self.local_to_gmt('%d/01/01 00:00:01' % (self.year))
        # Loop until it's next year:
        while (dt.tuple()[0] <= self.year):
            self.observer.date = dt
            risetime = self.observer.next_rising(ephem.Sun())
            self.observer.date = risetime
            settime = self.observer.next_setting(ephem.Sun())
            self.observer.date = settime

            # Now we're done setting observer time, so it's safe to
            # convert to localtime.
            risetime = self.local_mean_time(risetime)
            settime = self.local_mean_time(settime)
            risehours = self.ephemdate_to_hours(risetime)
            sethours = self.ephemdate_to_hours(settime)

            if risehours < self.ephemdate_to_hours(self.special_dates['earliest sunrise']):
                self.special_dates['earliest sunrise'] = risetime
            if risehours > self.ephemdate_to_hours(self.special_dates['latest sunrise']):
                self.special_dates['latest sunrise'] = risetime
            if sethours < self.ephemdate_to_hours(self.special_dates['earliest sunset']):
                self.special_dates['earliest sunset'] = settime
            if sethours > self.ephemdate_to_hours(self.special_dates['latest sunset']):
                self.special_dates['latest sunset'] = settime

            # calculate daylength in hours
            daylength = (settime - risetime) * 24.
            if daylength < self.special_dates['shortest day len']:
                self.special_dates['shortest day'] = risetime
                self.special_dates['shortest day len'] = daylength
            if daylength > self.special_dates['longest day len']:
                self.special_dates['longest day'] = risetime
                self.special_dates['longest day len'] = daylength

            dt = ephem.date(dt + ephem.hour * 24)

    def gmt_for_time_on_date(self, edate, timetuple):
        """Returns the ephem.date for the GMT corresponding to localtime
           timetuple on the given ephem.date.
        """
        tup = list(edate.tuple())
        tup[3], tup[4], tup[5] = timetuple
        return self.local_to_gmt(ephem.date(tuple(tup)), reverse=True)

    def draw_special_dates(self, timestr, labels=True):
        # Make a tuple out from timestr
        if ':' in timestr:
            timetuple = list(map(int, timestr.split(':')))
            while len(timetuple) < 3:
                timetuple.append(0)
        else:
            timetuple = (int(timestr), 0, 0)

        for key in self.special_dates:
            d = self.special_dates[key]
            if not isinstance(d, ephem.date):
                continue

            gmt = self.gmt_for_time_on_date(d, timetuple)
            self.observer.date = self.gmt_for_time_on_date(d, timetuple)
            # print(d, "gmt=", gmt)
            self.sun.compute(self.observer)
            # print("Computed", self.sun.az, self.sun.alt)
            x, y = self.project(self.sun.az, self.sun.alt)
            # print("x, y =", x, y)
            self.draw_dot(x, y, self.special_dot_size)

            if not labels:
                continue

            # Offsets to figure out where to draw the string.
            # That's tough, because they're normally on top of each other.
            # Latest sunrise is a little left of earliest sunset,
            # and shortest day is in between and a little below both.
            offsets = { "latest sunrise"   : (-1,  0),
                        "earliest sunset"  : ( 1,  0),
                        "shortest day"     : ( 0,  1),
                        "latest sunset"    : (-1,  0),
                        "earliest sunrise" : ( 1,  0),
                        "longest day"      : ( 0, -.5)
            }
            factor = 30
            xoffset = int(offsets[key][0] * factor)
            yoffset = int(offsets[key][1] * factor)
            self.draw_line(x, y, x + xoffset, y + yoffset)
            s = str(self.special_dates[key])
            if key + " len" in self.special_dates:
                # for longest/shortest days, split off the time part
                s = s.split(' ')[0]
                # and then add the day length
                s += ", %.1f hrs" % self.special_dates[key + " len"]
            self.draw_string(key + "\n" + s,
                             x + xoffset, y + yoffset, offsets=offsets[key])

        # Draw the equinoxes too. Solstices are too crowded what with
        # all the other special dates.

        def draw_equinox(start, whicheq, offsets):
            equinox = ephem.next_equinox(start)
            self.observer.date = self.gmt_for_time_on_date(equinox, (12, 0, 0))
            self.sun.compute(self.observer)
            x, y = self.project(self.sun.az, self.sun.alt)
            print("%s equinox: %s" % (whicheq, str(self.observer.date)))
            self.draw_dot(x, y, self.special_dot_size)

            if labels:
                x1 = x + offsets[0] * 20
                self.draw_line(x, y, x1, y)
                eqstr = "%s equinox\n%s" % (whicheq, str(equinox).split(' ')[0])
                self.draw_string(eqstr, x1, y, offsets)

        if observer.lat >= 0:    # Northern hemisphere
            draw_equinox("%d/1/1" % self.year, "Vernal", (-1, 0))
            draw_equinox(observer.date, "Autumnal", (1, 0))
        else:                    # Southern hemisphere
            draw_equinox("%d/1/1" % self.year, "Autumnal", (-1, 0))
            draw_equinox(observer.date+10, "Vernal", (1, 0))

    def special_dates_str(self):
        if not self.special_dates:
            try:
                self.calc_special_dates()
                # This can fail with ephem.AlwaysUpError in polar regions.
                return '''
Longest day: %d hours on %s
Shortest day: %d hours on %s
Earliest sunrise: %s
Latest sunrise: %s
Earliest sunset: %s
Latest sunset: %s
''' %                (self.special_dates["longest day len"],
                      str(self.special_dates["longest day"]),
                      self.special_dates["shortest day len"],
                      str(self.special_dates["shortest day"]),
                      str(self.special_dates["earliest sunrise"]),
                      str(self.special_dates["latest sunrise"]),
                      str(self.special_dates["earliest sunset"]),
                      str(self.special_dates["latest sunset"]))
            except (ephem.AlwaysUpError, ephem.NeverUpError):
                return 'Polar region: skipping special dates'

    def local_mean_time(self, d, reverse=False):
        """Adjust GMT to local time.
           We don't know time zone, but we can adjust for actual
           local noon since we know the Observer's longitude:
        """
        return ephem.date(ephem.date(d) \
                    + float(self.observer.lon) * 12 / math.pi * ephem.hour)

    def local_to_gmt(self, d, reverse=False):
        """Adjust GMT to local time.
           We don't know time zone, but we can adjust for actual
           local noon since we know the Observer's longitude:
        """
        return ephem.date(ephem.date(d) \
                    - float(self.observer.lon) * 12 / math.pi * ephem.hour)

    def ephemdate_to_hours(self, edate):
        if isinstance(edate, int):
            return edate
        etuple = edate.tuple()
        return etuple[3] + etuple[4]/60. + etuple[5]/3600.

    def draw_line(self, x1, y1, x2, y2, width=1):
        self.ctx.set_line_width(width)
        self.ctx.move_to(x1, y1)
        self.ctx.line_to(x2, y2)
        self.ctx.stroke()

    def draw_rectangle(self, x, y, width, height):
        self.ctx.rectangle(x, y, width, height)
        self.ctx.fill()

    def draw_dot(self, x, y, dotsize):
        if dotsize == 1:
            self.draw_line(x, y, x, y)

        elif dotsize <= 4:
            # Draw the dot centered, not hanging off to the lower right:
            x = int(x - dotsize / 2)
            y = int(y - dotsize / 2)
            self.draw_rectangle(x, y, dotsize, dotsize)
            self.ctx.fill()

        else:
            self.ctx.arc(x, y, dotsize, 0, 2*math.pi)
            self.ctx.fill()

    def draw_string(self, label, x, y, offsets=None):
        """Draw a string at the specified point.
           offsets is an optional tuple specifying where the string will
           be drawn relative to the coordinates passed in;
           for instance, if offsets are (-1, -1) the string will be
           drawn with the bottom right edge at the given x, y.
        """
        fontname = "Sans Italic 14"
        # fontname = "Sans Italic 14"

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
            if offsets[1] != 1:
                y += int(height * offsets[1] - height/2)

        self.ctx.move_to(x, y)
        PangoCairo.show_layout (self.ctx, layout)
        # self.ctx.show_text(label)

    def project_rectangular(self, az, alt):
        """Rectangular -- don't do any projection, just scaling"""

        span = math.pi * 1.2

        # if az < math.pi/2:
        #     az = math.pi - az
        # elif az > 3*math.pi/2:
        #     az = 3 * math.pi - az

        y = int((math.pi/2 - alt) * (self.height * 2 / math.pi))
        x = int(az * self.width / math.pi - self.width/2)

        return (x, y)

    def project_sinusoidal(self, lon, lat, dotsize=0):
        """Return a sinusoidal projection as (x, y)"""
        # XXX Actually this is bogus, it's not being used right for alt/az.

        # Sinusoidal projection
        y = int((math.pi/2 - lat) * self.height * 2 / math.pi)

        if lat > 90:
            return (0, 0)

        if lon < math.pi/2:
            self.ctx.set_source_rgb(*self.backside_color)
            lon = math.pi - lon
        elif lon > 3*math.pi/2:
            self.ctx.set_source_rgb(*self.backside_color)
            lon = 3 * math.pi - lon
        else:
            self.ctx.set_source_rgb(*self.sun_color)

        x = int(((lon - math.pi) * math.cos(lat) * self.width / math.pi)
                 + self.width/2)

        if dotsize > 0:
            self.draw_dot(x, y, dotsize)

        return (x, y)

    def project_and_draw(self, az, alt, dotsize=0):
        if az < math.pi/2 or az > 3*math.pi/2:
            self.ctx.set_source_rgb(*self.backside_color)
        else:
            self.ctx.set_source_rgb(*self.sun_color)

        x, y = self.project(az, alt)

        if dotsize > 0:
            self.draw_dot(x, y, dotsize)

    def project(self, az, alt, dotsize=0):
        if self.sinusoidal:
            return self.project_sinusoidal(az, alt)
        else:
            return self.project_rectangular(az, alt)

    def draw(self, widget, ctx, background=None, labels=True):
        """Draw everything: the analemma and all the labels.
           If background isn't passed, we'll default to
           self.background_color (opaque blue), but save_image()
           will pass in a transparent background.
        """
        self.ctx = ctx

        self.width, self.height = self.get_size()

        # Draw a blue background. But if we're using a sinusoidal
        # projection, then only color the projected part blue.
        if not background:
            background = self.background_color
        ctx.set_source_rgba(*background)
        if self.sinusoidal:
            self.draw_rectangle(0, 0, self.width, self.height)
            for f in range(0, int(math.pi * 100)):
                theta = f/200.
                (x, y) = self.project_sinusoidal(math.pi/2, theta)
                self.draw_rectangle(x, y, self.width - 2*x, 4)
        else:
            self.draw_rectangle(0, 0, self.width, self.height)

        # Draw some projected grid lines
        for f in range(0, int(math.pi * 100), 5):
            theta = f/200.   # i is going from 0 to pi/2
            # Draw the equator: (doesn't actually show up)
            # self.project_and_draw(theta + math.pi/2, 0., 1)
            # self.project_and_draw(theta + math.pi, 0., 1)

            # Central meridian (180 dgrees)
            self.project_and_draw(math.pi, theta, 1)

            # and a few other lines
            # self.project_and_draw(math.pi * .75, theta, 1)
            # self.project_and_draw(math.pi*1.25, theta, 1)

        # Then prepare to draw the sun in yellow:
        ctx.set_source_rgb(*self.sun_color)

        if self.lunar:
            # When is the moon on the meridian today?
            # Remember, it's self.sun even if it really is the moon.
            self.observer.date = ephem.now()
            # self.observer.date = ephem.Date('6/13/2005')
            transit = self.observer.next_transit(self.sun)

            # For testing, try replacing 30 with, say, 5000 to see the
            # motion of the moon over many years.
            for i in range(0, 30):
                self.draw_sun_position(transit)

                # Also draw lunar analemmas 4 hours earlier and later:
                self.draw_sun_position(ephem.Date(transit - 2.5 * ephem.hour))
                self.draw_sun_position(ephem.Date(transit + 2.5 * ephem.hour))

                # Increment the date.
                # How many minutes earlier does the moon rise each day?
                # Of course it varies because of the eccentricity
                # (and other complications) of the moon's orbit,
                # that being the whole point of looking for analemmas,
                # so what we want is the average time.
                #
                # But the actual number should be
                # (360 / 27.321661 - 360 / 365.25) * 24*60/360 = 48.76 hmm

                # (previous reasoning, wrong) 48.76 =
                # 24 * 60 / 29.530588853, days in a synodic month.
                # But in this simulation, 48.76 doesn't return the moon
                # to the same place after the end of a month.
                # 50.47 gives the tightest grouping.

                # += doesn't work on ephem.Dates, it converts to float.
                transit = ephem.Date(transit + 1.0 + 50.47 * ephem.minute)
                # transit = ephem.Date(transit + 1.0 + 48.76 * ephem.minute)

        else:
            # Calculate earliest sunrise and suchlike.
            self.calc_special_dates()

            # Draw three analemmas, showing the sun positions at 7:40 am,
            # noon, and 4:40 pm ... in each case adjusted for mean solar time,
            # i.e. the observer's position within their timezone.
            for time in [ '7:30', '12:00', '16:30' ]:
                for m in range(1, 13):
                    self.draw_sun_position('%d/%d/1 %s' % (self.year, m, time))
                    self.draw_sun_position('%d/%d/10 %s' % (self.year, m, time))
                    self.draw_sun_position('%d/%d/20 %s' % (self.year, m, time))

        # Mark special dates for mean solar noon.
        if not self.lunar:
            self.draw_special_dates("12:00", labels)

        if labels:
            # Make a label
            if observer.name == "custom":
                obslabel = "%.1f N, %.1f E" % (observer.lat, observer.lon)
            else:
                obslabel = self.observer.name
                # Split off lengthy labels that interfere with time labels
                if ", " in obslabel:
                    obslabel = obslabel.split(', ')[0]
            self.draw_string(obslabel, 10, 10)

    def save_image(self, outfile, labels=False):
        """Save the analemma as a PNG image, with the background
           transparent so it can be overlayed on top of a planetarium
           show, scenics, etc.
           Will save to a file named Analemma-$sitename.png
           with spaces replaced with dashes.
        """
        dst_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         self.width, self.height)

        dst_ctx = cairo.Context(dst_surface)

        # draw() will overwrite self.ctx, so save it first:
        save_ctx = self.ctx

        # Draw everything again to the new context,
        # with a transparent instead of an opaque background:
        self.draw(None, dst_ctx, (0, 0, 1, 0), labels)

        # Restore the GUI context:
        self.ctx = save_ctx

        dst_surface.write_to_png(outfile)
        print("Saved to", outfile)

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

    def show_window(self):
        self.drawing_area = Gtk.DrawingArea()
        self.set_default_size(1024, 450)   # was 512
        self.add(self.drawing_area)
        # self.connect("delete_event", Gtk.main_quit)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key_press)
        self.drawing_area.connect('draw', self.draw)
        self.show_all()
        Gtk.main()

def observer_for_city(city):
    try:
        return ephem.city(city)
    except KeyError:
        pass

    try:
        return cities.lookup(city)
    except ValueError:
        pass

    # Add some cities pyephem doesn't know:
    if city == 'San Jose':     # San Jose, CA at Houge Park
        observer = ephem.Observer()
        observer.name = "San Jose"
        observer.lon = '-121:56.8'
        observer.lat = '37:15.55'
        observer.elevation = 100
        return observer

    elif city == 'Los Alamos':  # Los Alamos, NM Nature Center
        observer = ephem.Observer()
        observer.name = "Los Alamos"
        observer.lon = '-106:18.36'
        observer.lat = '35:53.09'
        observer.elevation = 2100
        return observer

    elif city == 'White Rock':  # White Rock, NM Visitor Center
        observer = ephem.Observer()
        observer.name = "White Rock"
        observer.lon = '-106:12.75'
        observer.lat = '35:49.61'
        observer.elevation = 1960
        return observer

    return None

if __name__ == "__main__":
    def Usage():
        progname = os.path.basename(sys.argv[0])
        print("""Usage: %s [cityname [sun|moon]]
       %s lat lon [sun|moon]""" % (progname, progname))
        sys.exit(0)

    # We can optionally show an analemma of the moon rather than the sun.
    lunar = False

    # Is the last argument either "sun" or "moon"? If so, split it off.
    if sys.argv[-1] == 'sun':
        sys.argv = sys.argv[:-1]
    elif sys.argv[-1] == 'moon' or sys.argv[-1] == 'lunar':
        lunar = True
        sys.argv = sys.argv[:-1]

    if len(sys.argv) == 2:
        if sys.argv[1] == "-h" or sys.argv[1] == "--help":
            Usage()
        observer = observer_for_city(sys.argv[1])

    elif len(sys.argv) == 3:
        observer = ephem.Observer()
        observer.lat = sys.argv[1]
        observer.lon = sys.argv[2]
        observer.elevation = 100
        observer.name = "Observer at %s, %s" % (observer.lon, observer.lat)

    else:
        observer = observer_for_city('Los Alamos')

    if not observer:
        print("Can't find an observer for", ' '.join(sys.argv[1:]))
        sys.exit(1)
        # from ephem import cities
        # observer = cities.lookup('Los Alamos, NM')
        # but this is subject to Google rate lookup limits,
        # don't do it repeatedly

    awin = AnalemmaWindow(observer, ephem.now().triple()[0], lunar,
                          background=(0, 0, 0))
    print(awin.special_dates_str())
    awin.show_window()

