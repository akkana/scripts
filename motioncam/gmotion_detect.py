#!/usr/bin/env python

# Show a window for debugging or monitoring the motion detection code
# in motion_detect.py, using photos from piphoto.py.

# Copyright (C) 2014 Akkana Peck <akkana@shallowsky.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from __future__ import print_function

from gi import pygtkcompat
pygtkcompat.enable()
pygtkcompat.enable_gtk(version='3.0')

# import gtk, gobject, glib
import gtk, glib

import gc
import os
import sys
from PIL import Image

try:
    import RPi.GPIO as GPIO
except:
    pass

sys.path.insert(1, os.path.join(sys.path[0], '..'))

try:
    import ME007
    have_rangefinder = True
except:
    have_rangefinder = False

from motion_detect import MotionDetector

class MotionDetectorViewer() :
    '''
    '''
    def __init__(self, test_res, test_borders=None,
                 full_res=None,
                 localdir=None, remotedir=None,
                 secs=5,
                 rangefinder=None):
        self.test_res = test_res
        self.width = test_res[0]
        self.height = test_res[1]
        self.localdir = localdir
        self.remotedir = remotedir
        self.full_res = full_res
        self.millisecs = secs * 1000

        self.use_tmp_file = True

        self.win = gtk.Window()
        self.win.set_border_width(10)

        # Unfortunately delete and destroy events don't work on the RPi.
        # Not sure why, but most of the time the event never gets passed.
        # It works on other Linux platforms.
        self.win.connect("delete_event", self.quit)
        self.win.connect("destroy", self.quit)

        vbox = gtk.VBox(spacing=3)
        self.win.add(vbox)

        self.drawing_area = gtk.DrawingArea()
        self.drawing_area.set_size_request(self.width, self.height)
        #self.win.add(self.drawing_area)
        vbox.pack_start(self.drawing_area)

        self.drawing_area.set_events(gtk.gdk.EXPOSURE_MASK |
                                     # gtk.gdk.POINTER_MOTION_MASK |
                                     # gtk.gdk.POINTER_MOTION_HINT_MASK |
                                     gtk.gdk.BUTTON_PRESS_MASK |
                                     gtk.gdk.BUTTON_RELEASE_MASK )

        try:
            # GTK2:
            self.drawing_area.connect("expose-event", self.expose_handler)
        except TypeError:
            # Python3/GI GTK3:
            self.drawing_area.connect('size-allocate', self.on_size_allocate)
            self.width = self.height = 0
            self.drawing_area.connect('draw', self.expose3)

        self.drawing_area.connect("button_press_event", self.button_press)
        self.drawing_area.connect("button_release_event", self.button_release)
        self.drawing_area.connect("motion_notify_event", self.drag_handler)

        # Just for testing, temporarily
        self.num = 0

        glib.timeout_add(self.millisecs, self.idle_handler,
                         self.drawing_area)

        # GTK2: X GC
        self.gc = None

        self.redgc = None
        self.pixbuf = None
        self.imgwidth = None
        self.imgheight = None
        self.cur_img = None
        self.drag_start_x = None
        self.drag_start_y = None

        try:
            self.win.show_all()
        except:
            print("Couldn't show window: exiting")
            sys.exit(1)

        # And the motion detecting parts,
        # which are infinitely simpler than the GTK garbage:
        self.md = MotionDetector(test_res=test_res, test_borders=test_borders,
                                 full_res=self.full_res,
                                 sensitivity=400,
                                 threshold=30,
                                 localdir=self.localdir,
                                 remotedir=self.localdir,
                                 rangefinder=rangefinder,
                                 verbose=2)
        self.buf1 = None
        self.buf2 = None

    # There doesn't seem to be any way to predict reliably whether a
    # windowmanager delete event will pass 3 arguments or 2, so make
    # them all optional. We don't need them anyway.
    # Also, this is sometimes called twice (or, on the Pi, not at all).
    def quit(self, widget=None, event=None):
        print("Quitting")
        # Supposedly, return True if you don't want to close the window,
        # False if you do. In practice, neither one actually exits;
        # they just close the window and execution continues in such
        # a way that ctrl-C doesn't work and ctrl-\ and a core dump
        # is the only option.
        # return False

        # On the Pi, this crashes Python and dumps core:
        # gtk.main_quit()

        # This isn't what you're supposed to do, but it's the only
        # way I've found to actually exit without dumping core.
        sys.exit(0)

    def on_size_allocate(self, _unused, allocation):
        self.width = allocation.width
        self.height = allocation.height

    def expose3(self, _unused, _ctx):
        self.expose_handler(self.drawing_area, None)

    def expose_handler(self, widget, event):
        if not self.gc:
            try:
                self.gc = widget.window.new_gc()
                self.redgc = widget.window.new_gc()
                self.redgc.set_rgb_fg_color(gtk.gdk.Color(65535, 0, 0))
                self.redgc.line_width = 5
            except:
                pass
            #x, y, self.imgwidth, self.imgheight = self.get_allocation()

            # Have we had load_image called, but we weren't ready for it?
            # Now, theoretically, we are ... so call it again.
            if self.cur_img and not self.pixbuf :
                self.load_image(self.cur_img)

        self.show_image()

    def button_press(self, widget, event):
        print("Button press for button", event.button)
        if event.button != 1 :
            return False
        # For some reason, button press events give float arguments
        # though draw_line won't accept floats
        self.drag_start_x = int(event.x)
        self.drag_start_y = int(event.y)
        return True

    def button_release(self, widget, event):
        print("Button release for button", event.button)
        x = int(event.x)
        y = int(event.y)
        self.md.test_borders = [[[self.drag_start_x, x],
                                 [self.drag_start_y, y]]]
        print("Reset test borders to", self.md.test_borders)
        self.drag_start_x = None
        self.drag_start_y = None
        return True

    def drag_handler(self, widget, event):
        return True

    def load_image(self, img):
        '''Load the image passed in, and show it.
           Image can be a PIL Image or a filename.
           Return True for success, False for error.
        '''
        print("load_image", img)
        self.cur_img = img
        if not img:
            print("No image to load, returning")
            return

        # Is this a PIL Image? Does it have a mode attribute?
        if hasattr(img, 'mode'):
            print("Displaying the image already in memory")
            has_alpha = img.mode == 'RGBA'
            newpb = gtk.gdk.pixbuf_new_from_data(
                img.tobytes(),          # data
                gtk.gdk.COLORSPACE_RGB, # color mode
                has_alpha,
                8,                      # bits
                img.size[0],            # width
                img.size[1],            # height
                (has_alpha and 4 or 3) * img.size[0] # rowstride
                )
        # If it's not an image, assume it's a file.
        else:
            print("Reading an image in from", img)
            newpb = gtk.gdk.pixbuf_new_from_file(img)

        # Clean up memory from any existing pixbuf.
        # This still needs to be garbage collected before returning.
        if self.pixbuf :
            self.pixbuf = None

        try :
            self.pixbuf = newpb

        except glib.GError as e :
            print("glib error -- couldn't load")
            print(e)
            self.pixbuf = None

        # garbage collect the old pixbuf, if any, and the one we just read in:
        newpb = None
        gc.collect()

    def run(self):
        gtk.main()

    def clear(self):
        # Clear the drawing area
        self.drawing_area.window.draw_rectangle(self.gc, True, 0, 0,
                                                self.width, self.height)

    def show_image(self):
        if not self.pixbuf:
            print("No pixbuf!")
            return

        # GTK2?
        if self.gc:
            self.drawing_area.window.draw_pixbuf(self.gc, self.pixbuf,
                                                 0, 0, 0, 0)
            return

        # GTK3: all drawing is done through a Cairo context, cr.
        # It has to be created fresh each time.
        cr = self.drawing_area.get_window().cairo_create()

        # GTK3 pixbuf drawing seems to be almost completely undocumented.
        # The last two args of cairo_set_source_pixbuf are the point
        # on the canvas matching the (0, 0) point of the pixmap.
        gtk.gdk.cairo_set_source_pixbuf(cr, self.pixbuf, 0, 0)

        # Then these are the coordinates of the rectangle to draw
        # on the canvas.
        cr.rectangle(0, 0, self.width, self.height)

        # Some examples use paint() instead of fill();
        # I can't find any documentation explaining the difference,
        # but using paint() adds black borders around the images.
        cr.fill()

    # This is the function that actually takes and compares photos
    # every few seconds and does all the work.
    def idle_handler(self, widget):
        print()
        changed = False
        debugimage = None

        if not changed:
            if self.use_tmp_file:
                tmpfile = "/tmp/still.jpg"
                print("Snapping to", tmpfile)
                self.md.locam.take_still(outfile=tmpfile, res=self.test_res)
                im = Image.open(tmpfile)
            else:   # keep it all in memory, no temp files
                print("Snapping to memory")
                img_data = self.md.locam.take_still(outfile='-',
                                                    res=self.test_res)
                im = Image.open(img_data)

            changed, debugimage = self.md.compare_images(im)

        def red_frame():
            diff = 10
            if self.redgc:
                self.drawing_area.window.draw_rectangle(self.redgc, False,
                                                        diff, diff,
                                                        self.width-diff*2,
                                                        self.height-diff*2)
            else:    # cairo way
                cr = self.drawing_area.get_window().cairo_create()
                cr.set_source_rgb(1., 0., 0.)
                cr.rectangle(float(diff), float(diff),
                             float(self.width-diff*2),
                             float(self.height-diff*2))
                cr.stroke()

        if changed:
            print("**** They're different!")
            red_frame()
            self.md.snap_full_res()

        if debugimage:
            # debugimage.load()
            self.load_image(debugimage)
            self.show_image()
            # We just overwrote the frame, so re-draw it:
            if changed:
                red_frame()

        self.buf1 = self.buf2

        return True

if __name__ == '__main__':

    res=[320, 240]
    test_borders = [ [ [50, 270], [40, 200] ] ]
    localdir = os.path.expanduser('~/snapshots')
    if not os.path.exists(localdir):
        print(localdir, "doesn't exist, can't save any snapshots")
        sys.exit(1)
    remotedir = os.path.expanduser('~/moontrade/snapshots')
    #full_res = [3648, 2736]
    full_res = [1024, 768]

    rangefinder = ME007.ME007(trigger=23, echo=24) if have_rangefinder else None
    md = MotionDetectorViewer(test_res=res, test_borders=test_borders,
                              full_res=full_res,
                              localdir=localdir, remotedir=remotedir,
                              secs=5,
                              rangefinder=rangefinder)

    try:
        md.run()
    except KeyboardInterrupt:
        print("Bye")
        if 'GPIO' in sys.modules:
            GPIO.cleanup()

