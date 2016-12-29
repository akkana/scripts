#! /usr/bin/env python

# Display an analemma for a specified location and time.
# Copyright 2011 by Akkana Peck: share and enjoy under the GPL v2 or later.

import gtk
import ephem
import sys, math

class AnalemmaWindow:
    def __init__(self):
        self.drawing_area = None
        self.xgc = None
        self.bgc = None
        self.width = 0
        self.height = 0
        self.observer = None
        self.sun = ephem.Sun()
        self.sinusoidal = False

    def draw(self, gc, x, y, dotsize):
        if dotsize == 1:
            self.drawing_area.window.draw_points(gc, [(x, y)])
        elif dotsize <= 4:
            self.drawing_area.window.draw_rectangle(gc, True, x, y,
                                                    dotsize, dotsize)
        else:
            self.drawing_area.window.draw_arc(gc, True, x, y,
                                              dotsize, dotsize, 0, 23040)

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
            self.draw(gc, x, y, dotsize)

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
            self.draw(gc, x, y, dotsize)

    def project(self, az, alt):
        if self.sinusoidal:
            return self.project_sinusoidal(az, alt)
        else:
            return self.project_rectangular(az, alt)

    def draw_sun_position(self, date):
        if not self.drawing_area:
            print "no drawing area"
            return
        if not self.xgc:
            print "no GC"
            return

        # We don't know time zone, but we can adjust for actual
        # local noon since we know the Observer's longitude:
        adjtime = ephem.date(ephem.date(date) \
                        - float(self.observer.lon) * 12 / math.pi * ephem.hour)
        observer.date = adjtime

        self.sun.compute(self.observer)

        # Y scale is 90 degrees (PI/2), horizon to zenith:
        # y = self.height - int(float(self.sun.alt) * self.height / math.pi * 2)

        # So make X scale 90 degrees too, centered around due south.
        # Want az = PI to come out at x = width/2,
        # az = PI/2 to be 0, 3*PI/2 = width.
        # x = int(float(self.sun.az) * self.width / math.pi * 2 - self.width / 2) % self.width

        self.project_and_draw(self.sun.az, self.sun.alt, 4)

    def expose_handler(self, widget, event):
        # print "Expose"
        if not self.xgc:
            self.xgc = widget.window.new_gc()
            self.bgc = widget.window.new_gc()
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

        # Draw some projected grid lines
        #self.xgc.set_rgb_fg_color(gtk.gdk.Color(16384, 16384, 16384))
        self.xgc.set_rgb_fg_color(gtk.gdk.Color(65535, 65535, 65535))
        for f in range(0, int(math.pi * 100), 5):
            theta = f/200.   # i is going from 0 to pi/2
            # Draw the equator:
            self.project_and_draw(theta + math.pi/2, 0., 1)
            self.project_and_draw(theta + math.pi, 0., 1)

            # Central meridian (180 dgrees)
            self.project_and_draw(math.pi, theta, 1)

            # Draw the edges of the plot
            self.project_and_draw(math.pi/2, theta, 1)
            self.project_and_draw(math.pi*3/2, theta, 1)

            # and a few other lines
            self.project_and_draw(math.pi * .75, theta, 1)
            self.project_and_draw(math.pi*1.25, theta, 1)

        # Then prepare to draw the sun in yellow:
        self.xgc.set_rgb_fg_color(gtk.gdk.Color(65535, 65535, 0))

        # the "backside" GC will have a different color
        self.bgc.set_rgb_fg_color(gtk.gdk.Color(65535, 32767, 0))

        # Draw three analemmas, showing the sun positions at 7:40 am,
        # noon, and 4:40 pm ... in each case adjusted for mean solar time,
        # i.e. the observer's position within their timezone.
        for time in [ '8:00', '12:00', '16:00' ]:
            for m in range(1, 13):
                self.draw_sun_position('2011/%d/1 %s' % (m, time))
                self.draw_sun_position('2011/%d/10 %s' % (m, time))
                self.draw_sun_position('2011/%d/20 %s' % (m, time))

        layout = self.drawing_area.create_pango_layout("Observer: " +
                                                       self.observer.name)
        # layout.set_font_description(self.font_desc)
        self.drawing_area.window.draw_layout(self.xgc, 10, 10, layout)

    def show_window(self, observer):
        self.observer = observer
        win = gtk.Window()
        self.drawing_area = gtk.DrawingArea()
        self.drawing_area.connect("expose-event", self.expose_handler)
        win.add(self.drawing_area)
        self.drawing_area.show()
        win.connect("destroy", gtk.main_quit)
        win.set_default_size(1025, 512)
        win.show()
        gtk.main()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        observer = ephem.city(sys.argv[1])
    elif len(sys.argv) == 3:
        observer = ephem.Observer()
        observer.name = "custom"
        observer.lon = sys.argv[1]
        observer.lat = sys.argv[2]
    else:
        # default to San Jose
        # pyephem doesn't know ephem.city('San Jose')
        # Houge Park is -121^56.53' 37^15.38'
        observer = ephem.Observer()
        observer.name = "San Jose"
        observer.lon = '-121:56.8'
        observer.lat = '37:15.55'
        observer.elevation = 100

    awin = AnalemmaWindow()
    awin.show_window(observer)

