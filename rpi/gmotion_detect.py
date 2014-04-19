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

import gtk, gobject, glib
import gc
from PIL import Image

from piphoto import take_still

from motion_detect import MotionDetector

class MotionDetectorViewer() :
    '''
    '''
    def __init__(self, test_res, test_borders=None):
        self.test_res = test_res
        self.width = test_res[0]
        self.height = test_res[1]

        self.win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.win.set_border_width(10)

        self.win.connect("delete_event", gtk.main_quit)
        self.win.connect("destroy", gtk.main_quit)

        self.drawing_area = gtk.DrawingArea()
        self.drawing_area.set_size_request(self.width, self.height)
        self.win.add(self.drawing_area)

        self.drawing_area.connect("expose-event", self.expose_handler)

        # Just for testing, temporarily
        self.num = 0

        gobject.timeout_add(2000, self.idle_handler, self.drawing_area)

        self.gc = None
        self.pixbuf = None
        self.imgwidth = None
        self.imgheight = None
        self.cur_img = None

        self.win.show_all()

        # And the motion detecting parts,
        # which are infinitely simpler than the GTK garbage:
        self.md = MotionDetector(test_res=test_res, test_borders=test_borders,
                                 verbose=2)
        self.buf1 = None
        self.buf2 = None

    def expose_handler(self, widget, event):
        #print "Expose"

        if not self.gc :
            self.gc = widget.window.new_gc()
            #x, y, self.imgwidth, self.imgheight = self.get_allocation()

            # Have we had load_image called, but we weren't ready for it?
            # Now, theoretically, we are ... so call it again.
            if self.cur_img and not self.pixbuf :
                self.load_image(self.cur_img)

        self.show_image()

    def load_image(self, filename):
        '''Load the image passed in, and show it.
           Return True for success, False for error.
        '''
        self.cur_img = filename

        # Clean up memory from any existing pixbuf.
        # This still needs to be garbage collected before returning.
        if self.pixbuf :
            self.pixbuf = None

        try :
            newpb = gtk.gdk.pixbuf_new_from_file(filename)
            self.pixbuf = newpb

        except glib.GError, e :
            print "glib error -- couldn't load"
            print e
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
        if not self.gc:
            return

        if not self.pixbuf:
            return

        self.drawing_area.window.draw_pixbuf(self.gc, self.pixbuf, 0, 0, 0, 0)

    def idle_handler(self, widget):

        print "\n"
        tmpfile = "/tmp/still.jpg"
        take_still(outfile=tmpfile, res=self.test_res, verbose=False)
        im = Image.open(tmpfile)
        different = self.md.compare_images(im)
        if different:
            print "They're different!"
        self.load_image('/tmp/debug.png')
        self.show_image()

        self.buf1 = self.buf2

        return True

if __name__ == '__main__':

    import time

    res=[320, 240]
    test_borders = [ [ [140, 180], [105, 135] ] ]
    md = MotionDetectorViewer(test_res=res, test_borders=test_borders)

    #iv.load_image('/home/akkana/src/pho/test-img/1.jpg')
    md.run()


