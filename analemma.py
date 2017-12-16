#! /usr/bin/env python

# Display an analemma for a specified location and time.
# Copyright 2011 by Akkana Peck: share and enjoy under the GPL v2 or later.

import gtk
import ephem
import sys
import os
import math

class AnalemmaWindow:
    def __init__(self, observer, year):
        self.observer = observer
        self.year = year

        self.special_dates = None
        self.drawing_area = None
        self.xgc = None
        self.bgc = None
        self.specialgc = None
        self.width = 0
        self.height = 0
        self.sun = ephem.Sun()
        self.sinusoidal = False

    def draw_sun_position(self, date):
        if not self.drawing_area:
            print "no drawing area"
            return
        if not self.xgc:
            print "no GC"
            return
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
        '''Earlist and latest rising and setting times,
           and longest/shortest day.
        '''
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
        while (dt.tuple()[0] == self.year):
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
        '''Returns the ephem.date for the GMT corresponding to localtime
           timetuple on the given ephem.date.
        '''
        tup = list(edate.tuple())
        tup[3], tup[4], tup[5] = timetuple
        return self.local_to_gmt(ephem.date(tuple(tup)), reverse=True)

    def draw_special_dates(self, timestr):
        # Make a tuple out from timestr
        if ':' in timestr:
            timetuple = map(int, timestr.split(':'))
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
            self.sun.compute(self.observer)
            x, y = self.project(self.sun.az, self.sun.alt)
            self.draw_dot(self.specialgc, x, y, 7)

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
            self.drawing_area.window.draw_line(self.specialgc, x, y,
                                               x + xoffset, y + yoffset)
            s = str(self.special_dates[key])
            if key + " len" in self.special_dates:
                # for longest/shortest days, split off the time part
                s = s.split(' ')[0]
                # and then add the day length
                s += ", %.1f hrs" % self.special_dates[key + " len"]
            self.draw_string(key + "\n" + s,
                             x + xoffset, y + yoffset, self.specialgc,
                             offsets=offsets[key])

        # Draw the equinoxes too. Solstices are too crowded what with
        # all the other special dates.

        def draw_equinox(start, whicheq, offsets):
            equinox = ephem.next_equinox(start)
            self.observer.date = self.gmt_for_time_on_date(equinox, (12, 0, 0))
            self.sun.compute(self.observer)
            x, y = self.project(self.sun.az, self.sun.alt)
            self.draw_dot(self.specialgc, x, y, 7)
            x1 = x + offsets[0] * 20
            self.drawing_area.window.draw_line(self.specialgc, x, y, x1, y)
            eqstr = "%s equinox\n%s" % (whicheq, str(equinox).split(' ')[0])
            self.draw_string(eqstr, x1, y, self.specialgc, offsets)

        draw_equinox("%d/1/1" % self.year, "Vernal", (-1, 0))
        draw_equinox(observer.date, "Autumnal", (1, 0))

    def special_dates_str(self):
        if not self.special_dates:
            self.calc_special_dates()
        s = '''
Longest day: %d hours on %s
Shortest day: %d hours on %s
Earliest sunrise: %s
Latest sunrise: %s
Earliest sunset: %s
Latest sunset: %s
''' %      (self.special_dates["longest day len"],
            str(self.special_dates["longest day"]),
            self.special_dates["shortest day len"],
            str(self.special_dates["shortest day"]),
            str(self.special_dates["earliest sunrise"]),
            str(self.special_dates["latest sunrise"]),
            str(self.special_dates["earliest sunset"]),
            str(self.special_dates["latest sunset"]))
        return s

    def local_mean_time(self, d, reverse=False):
        '''Adjust GMT to local time.
           We don't know time zone, but we can adjust for actual
           local noon since we know the Observer's longitude:
        '''
        return ephem.date(ephem.date(d) \
                    + float(self.observer.lon) * 12 / math.pi * ephem.hour)

    def local_to_gmt(self, d, reverse=False):
        '''Adjust GMT to local time.
           We don't know time zone, but we can adjust for actual
           local noon since we know the Observer's longitude:
        '''
        return ephem.date(ephem.date(d) \
                    - float(self.observer.lon) * 12 / math.pi * ephem.hour)

    def ephemdate_to_hours(self, edate):
        if isinstance(edate, int):
            return edate
        etuple = edate.tuple()
        return etuple[3] + etuple[4]/60. + etuple[5]/3600.

    def draw_dot(self, gc, x, y, dotsize):
        # Draw the dot centered, not hanging off to the lower right:
        x = int(x - dotsize / 2)
        y = int(y - dotsize / 2)

        if dotsize == 1:
            self.drawing_area.window.draw_points(gc, [(x, y)])
        elif dotsize <= 4:
            self.drawing_area.window.draw_rectangle(gc, True, x, y,
                                                    dotsize, dotsize)
        else:
            self.drawing_area.window.draw_arc(gc, True, x, y,
                                              dotsize, dotsize, 0, 23040)

    def draw_string(self, label, x, y, gc=None, offsets=None):
        '''Draw a string at the specified point.
           offsets is an optional tuple specifying where the string will
           be drawn relative to the coordinates passed in;
           for instance, if offsets are (-1, -1) the string will be
           drawn with the bottom right edge at the given x, y.
        '''
        layout = self.drawing_area.create_pango_layout(label)
        # layout.set_font_description(self.font_desc)
        if not gc:
            gc = self.xgc
        if offsets:
            # pango draws text with the upper left corner at x, y.
            # So that's an offset of (1, 1). Adjust if offsets are different.
            width, height = layout.get_pixel_size()
            if offsets[0] == 0:
                x -= int(width/2)
            elif offsets[0] != 1:
                x += int(width * offsets[0])
            if offsets[1] != 1:
                y += int(height * offsets[1] - height/2)
        self.drawing_area.window.draw_layout(gc, x, y, layout)

    def project_rectangular(self, az, alt):
        """Rectangular -- don't do any projection, just scaling"""

        y = int((math.pi/2 - alt) * (self.height * 2 / math.pi))
        x = int(az * self.width / math.pi - self.width/2)

        return (x, y)

    def project_sinusoidal(self, lon, lat):
        """Return a sinusoidal projection as (x, y)"""
        # XXX Actually this is bogus, it's not being used right for alt/az.

        # Sinusoidal projection
        y = int((math.pi/2 - lat) * self.height * 2 / math.pi)

        if lat > 90:
            print "lat is", lat
            return (0, 0)

        if lon < math.pi/2:
            gc = self.bgc
            lon = math.pi - lon
        elif lon > 3*math.pi/2:
            gc = self.bgc
            lon = 3 * math.pi - lon
        else:
            gc = self.xgc

        x = int(((lon - math.pi) * math.cos(lat) * self.width / math.pi)
                 + self.width/2)

        if dotsize > 0:
            self.draw_dot(gc, x, y, dotsize)

        #print int(lon*180/math.pi), int(lat*180/math.pi), x, y

        return (x, y)

    def project_and_draw(self, az, alt, dotsize):
        if az < math.pi/2:
            gc = self.bgc
            az = math.pi - az
        elif az > 3*math.pi/2:
            gc = self.bgc
            az = 3 * math.pi - az
        else:
            gc = self.xgc

        x, y = self.project(az, alt)

        if dotsize > 0:
            self.draw_dot(gc, x, y, dotsize)

    def project(self, az, alt):
        if self.sinusoidal:
            return self.project_sinusoidal(az, alt)
        else:
            return self.project_rectangular(az, alt)

    def expose_handler(self, widget, event):
        # print "Expose"
        if not self.xgc:
            self.xgc = widget.window.new_gc()
            self.bgc = widget.window.new_gc()
            self.specialgc = widget.window.new_gc()
        self.width, self.height = self.drawing_area.window.get_size()

        # Draw a blue background. But if we're using a sinusoidal
        # projection, then only color the projected part blue.
        self.xgc.set_rgb_fg_color(gtk.gdk.Color(0, 0, 65535))
        if self.sinusoidal:
        # the "backside" GC will have a different color
            self.bgc.set_rgb_fg_color(gtk.gdk.Color(0, 0, 0))
            self.drawing_area.window.draw_rectangle(self.bgc, True, 0, 0,
                                                    self.width, self.height)
            for f in range(0, int(math.pi * 100)):
                theta = f/200.
                (x, y) = self.project_sinusoidal(math.pi/2, theta, 0)
                #print f, theta, x, y
                self.drawing_area.window.draw_rectangle(self.xgc, True,
                                                        x, y,
                                                        self.width - 2*x, 4)
        else:
            self.drawing_area.window.draw_rectangle(self.xgc, True, 0, 0,
                                                    self.width, self.height)

        # "Special" gc to be used for showing special dates
        self.specialgc.set_rgb_fg_color(gtk.gdk.Color(65535, 65535, 65535))

        # Draw some projected grid lines
        #self.xgc.set_rgb_fg_color(gtk.gdk.Color(16384, 16384, 16384))
        self.xgc.set_rgb_fg_color(gtk.gdk.Color(65535, 65535, 65535))
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
        self.xgc.set_rgb_fg_color(gtk.gdk.Color(65535, 65535, 0))

        # the "backside" GC will have a different color
        self.bgc.set_rgb_fg_color(gtk.gdk.Color(65535, 32767, 0))

        # Calculate earliest sunrise and suchlike.
        self.calc_special_dates()

        # Draw three analemmas, showing the sun positions at 7:40 am,
        # noon, and 4:40 pm ... in each case adjusted for mean solar time,
        # i.e. the observer's position within their timezone.
        for time in [ '8:00', '12:00', '16:00' ]:
            for m in range(1, 13):
                self.draw_sun_position('%d/%d/1 %s' % (self.year, m, time))
                self.draw_sun_position('%d/%d/10 %s' % (self.year, m, time))
                self.draw_sun_position('%d/%d/20 %s' % (self.year, m, time))

        # Mark special dates for mean solar noon.
        self.draw_special_dates("12:00")

        # Make a label
        if observer.name == "custom":
            obslabel = "Observer at %.1f N, %.1f E" % (observer.lat,
                                                       observer.lon)
        else:
            obslabel = "Observer in " + self.observer.name
        self.draw_string(obslabel, 10, 10)

    def save(self):
        print "Saved"

    def key_press(self, widget, event):
        if event.string == "q":
            gtk.main_quit()
        if event.keyval == gtk.keysyms.s and \
           event.state == gtk.gdk.CONTROL_MASK:
            self.save()
            return True
        return False

    def show_window(self):
        win = gtk.Window()
        self.drawing_area = gtk.DrawingArea()
        self.drawing_area.connect("expose-event", self.expose_handler)
        win.connect("key-press-event", self.key_press)
        win.add(self.drawing_area)
        self.drawing_area.show()
        win.connect("destroy", gtk.main_quit)
        win.set_default_size(1025, 512)
        win.show()
        gtk.main()

def observer_for_city(city):
    try:
        observer = ephem.city(city)
        return observer
    except KeyError:
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
        print """Usage: %s [cityname]
       %s [lat lon]""" % (progname, progname)
        sys.exit(0)
    if len(sys.argv) == 2:
        if sys.argv[1] == "-h" or sys.argv[1] == "--help":
            Usage()
        observer = observer_for_city(sys.argv[1])

    elif len(sys.argv) == 3:
        observer = ephem.Observer()
        observer.name = "custom"
        observer.lon = sys.argv[1]
        observer.lat = sys.argv[2]

    else:
        observer = observer_for_city('Los Alamos')

    if not observer:
        print "Can't find an observer for", ' '.join(sys.argv[1:])

    awin = AnalemmaWindow(observer, ephem.now().triple()[0])
    print awin.special_dates_str()
    awin.show_window()

