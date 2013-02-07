#! /usr/bin/env python

# Display an analemma for a specified location and time.
# Copyright 2011 by Akkana Peck: share and enjoy under the GPL v2 or later.

import gtk
import ephem
import sys, math

class AnalemmaWindow :
    def __init__(self) :
        self.drawing_area = None
        self.xgc = None
        self.bgc = None
        self.width = 0
        self.height = 0
        self.observer = None
        self.sun = ephem.Sun()
        self.sinusoidal = True

    def draw(self, gc, x, y, dotsize) :
        if dotsize == 1 :
            self.drawing_area.window.draw_points(gc, [(x, y)])
        elif dotsize <= 4 :
            self.drawing_area.window.draw_rectangle(gc, True, x, y,
                                                    dotsize, dotsize)
        else :
            self.drawing_area.window.draw_arc(gc, True, x, y,
                                              dotsize, dotsize, 0, 23040)

    def project_rectangular(self, lon, lat, dotsize) :
        """Rectangular -- don't do any projection, just scaling"""
        if lon < math.pi/2 :
            gc = self.bgc
            lon = math.pi - lon
        elif lon > 3*math.pi/2 :
            gc = self.bgc
            lon = 3 * math.pi - lon
        else :
            gc = self.xgc

        y = int((math.pi/2 - lat) * (self.height * 2 / math.pi))
        x = int(lon * self.width / math.pi - self.width/2)
        if dotsize > 0 :
            self.draw(gc, x, y, dotsize)

        return (x, y)

    def project_sinusoidal(self, lon, lat, dotsize) :
        """Return a sinusoidal projection as (x, y)"""

        # Sinusoidal projection
        y = int((math.pi/2 - lat) * self.height * 2 / math.pi)

        if lat > 90 :
            print "lat is", lat
            return (0, 0)

        if lon < math.pi/2 :
            gc = self.bgc
            lon = math.pi - lon
        elif lon > 3*math.pi/2 :
            gc = self.bgc
            lon = 3 * math.pi - lon
        else :
            gc = self.xgc

        x = int(((lon - math.pi) * math.cos(lat) * self.width / math.pi)
                 + self.width/2)

        if dotsize > 0 :
            self.draw(gc, x, y, dotsize)

        #print int(lon*180/math.pi), int(lat*180/math.pi), x, y

        return (x, y)

    def project(self, lon, lat, dotsize) :
        if self.sinusoidal :
            self.project_sinusoidal(lon, lat, dotsize)
        else :
            self.project_rectangular(lon, lat, dotsize)

    def sun_position(self, date) :
        if not self.drawing_area :
            print "no drawing area"
            return
        if not self.xgc :
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

        self.project(self.sun.az, self.sun.alt, 4)

    def expose_handler(self, widget, event) :
        # print "Expose"
        if not self.xgc :
            self.xgc = widget.window.new_gc()
            self.bgc = widget.window.new_gc()
        self.width, self.height = self.drawing_area.window.get_size()

        # Draw a blue background. But if we're using a sinusoidal
        # projection, then only color the projected part blue.
        self.xgc.set_rgb_fg_color(gtk.gdk.Color(0, 0, 65535))
        if self.sinusoidal :
        # the "backside" GC will have a different color
            self.bgc.set_rgb_fg_color(gtk.gdk.Color(0, 0, 0))
            self.drawing_area.window.draw_rectangle(self.bgc, True, 0, 0,
                                                    self.width, self.height)
            for f in range(0, int(math.pi * 100)) :
                theta = f/200.
                (x, y) = self.project_sinusoidal(math.pi/2, theta, 0)
                #print f, theta, x, y
                self.drawing_area.window.draw_rectangle(self.xgc, True,
                                                        x, y,
                                                        self.width - 2*x, 4)
        else :
            self.drawing_area.window.draw_rectangle(self.xgc, True, 0, 0,
                                                    self.width, self.height)

        # Draw some projected grid lines
        #self.xgc.set_rgb_fg_color(gtk.gdk.Color(16384, 16384, 16384))
        self.xgc.set_rgb_fg_color(gtk.gdk.Color(65535, 65535, 65535))
        for f in range(0, int(math.pi * 100), 5) :
            theta = f/200.   # i is going from 0 to pi/2
            # Draw the equator:
            self.project(theta + math.pi/2, 0., 1)
            self.project(theta + math.pi, 0., 1)

            # Central meridian (180 dgrees)
            self.project(math.pi, theta, 1)

            # Draw the edges of the plot
            self.project(math.pi/2, theta, 1)
            self.project(math.pi*3/2, theta, 1)

            # and a few other lines
            self.project(math.pi * .75, theta, 1)
            self.project(math.pi*1.25, theta, 1)

        # Then prepare to draw the sun in yellow:
        self.xgc.set_rgb_fg_color(gtk.gdk.Color(65535, 65535, 0))

        # the "backside" GC will have a different color
        self.bgc.set_rgb_fg_color(gtk.gdk.Color(65535, 32767, 0))

        #for time in [ '15:30', '20:00', '0:30' ] :   # Times are always GMT
        for time in [ '7:30', '12:00', '16:30' ] :
        #for time in [ '12:00' ] :
            for m in range(1, 13) :
                self.sun_position('2011/%d/1 %s' % (m, time))
                self.sun_position('2011/%d/10 %s' % (m, time))
                self.sun_position('2011/%d/20 %s' % (m, time))

    def show_window(self, observer) :
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

if __name__ == "__main__" :
    if len(sys.argv) == 2 :
        observer = ephem.city(sys.argv[1])
    elif len(sys.argv) == 3 :
        observer = ephem.Observer()
        observer.name = "custom"
        observer.lon = sys.argv[1]
        observer.lat = sys.argv[2]
    else :
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

