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

    def key_press_event(self, widget, event):
        """Handle a key press event anywhere in the window"""
        if event.string == " ":
            imagewin.next_image()
            return
        elif event.string == "q":
            gtk.main_quit()
            return

if __name__ == '__main__':
    win = TransImageViewerWindow(sys.argv[1:])
    win.run()
