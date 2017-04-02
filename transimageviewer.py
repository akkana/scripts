#!/usr/bin/env python

# A translucent window that passes events through.
# To see this under openbox, run xcompmgr -c -t-6 -l-6 -o.2 &
# or whatever compositor you prefer.
# Copyright 2017 by Akkana Peck, share and enjoy under the GPLv2 or later.

import cairo
import gtk

from imageviewer import ImageViewerWindow

import sys
import os
import math

class TransImageViewerWindow(ImageViewerWindow):
    def __init__(self, file_list=None, width=1024, height=768):
        super(TransImageViewerWindow, self).__init__(file_list, width, height)

        self.connect("configure-event", self.expose)
        self.connect("key-press-event", self.key_press_event)

        self.set_opacity(.5)

    def expose(self, widget, event):
        # Set our shape mask, so mouse events pass through
        # to the window underneath.
        if self.is_composited():
            region = gtk.gdk.region_rectangle(gtk.gdk.Rectangle(0, 0, 1, 1))
            self.window.input_shape_combine_region(region, 0, 0)
        else:
            print "Not composited"

    def shapeinput_mask(self):
        self.pixmap = gtk.gdk.Pixmap(None, self.width, self.height, 1)
        ctx = self.pixmap.cairo_create()
        #self.bgpb = gtk.gdk.pixbuf_new_from_file('base.png')
        ctx.save()
        ctx.set_source_rgba(1, 1, 1,0)
        ctx.set_operator (cairo.OPERATOR_SOURCE)
        ctx.paint()
        ctx.restore()

        # https://lists.cairographics.org/archives/cairo/2006-February/006362.html
        def make_bitmap(circle=False):
            bitmap = gtk.gdk.Pixmap(None, self.width, self.height, 1)
            cr = bitmap.cairo_create()


            # If requested, make a white circle in a black rect:
            if circle:
                # fill bitmap with black
                cr.rectangle (0, 0, self.width, self.height)
                cr.set_operator(cairo.OPERATOR_CLEAR)
                cr.fill();

                # draw white filled circle
                cr.arc(self.width / 2, self.height / 2, self.width / 4,
                       0, 2 * math.pi);
                cr.set_operator(cairo.OPERATOR_OVER);
                cr.fill();
            # else make an all-white rect:
            else:
                # fill bitmap with white
                cr.rectangle (0, 0, self.width, self.height)
                cr.set_operator(cairo.OPERATOR_CLEAR)
                cr.fill();

                # Draw black up near the top so we can still have a titlebar
                cr.rectangle (0, 0, self.width, 50)
                cr.set_operator(cairo.OPERATOR_OVER)
                cr.fill();

            return bitmap

        circle_bitmap = make_bitmap(True)
        rect_bitmap = make_bitmap(False)

        if self.is_composited():
            print "It's composited"
            ctx.rectangle(0, 0, 800, 600)
            ctx.fill()
            self.window.shape_combine_mask(circle_bitmap, 0, 0)
            self.window.input_shape_combine_mask(rect_bitmap, 0, 0)
        else:
            print "Not composited"
            self.window.shape_combine_mask(shape_bitmap, 0, 0)

    def key_press_event(self, widget, event):
        '''Handle a key press event anywhere in the window'''
        if event.string == " ":
            imagewin.next_image()
            return
        if event.string == "q":
            gtk.main_quit()
            return

if __name__ == '__main__':
    win = TransImageViewerWindow(sys.argv[1:])
    win.run()
