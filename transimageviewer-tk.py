#!/usr/bin/env python3

# A translucent image viewer in Tk.
# It tries to use an Xlib technique to allow clicking through,
# but unfortunately I never got that working.

# Xlib parts from https://raw.githubusercontent.com/python-xlib/python-xlib/master/examples/shapewin.py

from tkinter import Tk, NW, Canvas

from PIL import ImageTk, Image

from Xlib import X, display, Xutil
from Xlib.error import BadWindow
from Xlib.ext import shape

import time
import sys, os


# An X11 class Tk will use to make its main window identifiable to Xlib.
BOGO_CLASS = "tktransimage %s" % os.getpid()


def trans_image_window(imgfile, opacity=1):
    img = Image.open(imgfile)

    tkroot = Tk(baseName=BOGO_CLASS, className=BOGO_CLASS)

    canvas = Canvas(tkroot)   # , width=img.width, height=img.height)
    canvas.pack()

    # tkroot.geometry("=%dx%d" % (img.width, img.height))

    canvas.config(width=img.width, height=img.height)

    imgtk = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, anchor=NW, image=imgtk)

    tkroot.wait_visibility(tkroot)

    # Make the window translucent
    tkroot.attributes('-alpha', opacity)

    # It's important to return imgtk, otherwise it will get
    # garbage collected and won't be displayed.
    return tkroot, canvas, imgtk


def add_xlib_clickthrough():
    """Attempt to add clickthrough to the currently focused window,
       using Xlib's SHAPE extension.
       Doesn't work on a window created with Tk.
    """
    dpy = display.Display()
    if not dpy.has_extension('SHAPE'):
        sys.stderr.write('%s: server does not have SHAPE extension\n'
                         % os.path.basename(sys.argv[0]))
        sys.exit(1)

    # TkInter offers no direct way to get the X ID, and TkInter windows
    # are hidden so they don't show up in xlsclients/xroot.query_tree().
    # So here's a horrible hack: the windowmanager should give focus to
    # the window that just became visible, so assume the focused window
    # is the current one.
    # time.sleep(2)
    xwin = dpy.get_input_focus().focus
    # Check to make sure it's right:
    if xwin.get_wm_class()[0] != BOGO_CLASS:
        print("wm_class:", xwin.get_wm_class())
        print("Focused window wasn't the one just created. Bailing.")
        sys.exit(0)
    # print("xwin:", xwin)

    #
    # create a pixmap for the input shape
    #
    screen = dpy.screen()
    geom = xwin.get_geometry()
    print(geom.width, geom.height)
    shape_pm = screen.root.create_pixmap(geom.width, geom.height, 1)
    input_pm = screen.root.create_pixmap(geom.width, geom.height, 1)
    gc = screen.root.create_gc(foreground=screen.white_pixel,
                               background=screen.black_pixel)
    shape_pm.fill_rectangle(gc, 0, 0, geom.width, geom.height)
    input_pm.fill_rectangle(gc, 0, 0, geom.width, geom.height)
    gc.change(foreground=screen.black_pixel)
    shape_pm.fill_rectangle(gc, 100, 100, 800, 600)
    gc.free()

    # SO options are Intersect, Invert, Set, Subtract, Union
    # SK options are Bounding, Clip, Input
    # See https://www.x.org/releases/X11R7.7/doc/libXext/shapelib.html
    # Bounding is what moonroot uses.
    xwin.shape_mask(shape.SO.Set, shape.SK.Clip, 0, 0, shape_pm)
    # xwin.shape_mask(shape.SO.Set, shape.SK.Input, 0, 0, shape_pm)


if __name__ == '__main__':
    tkroot, imagewin, imgtk = trans_image_window(sys.argv[1],
                                                 opacity=.5)
    add_xlib_clickthrough()

    # Trap 'q' keypress to exit
    def keypress(e):
        if e.char == 'q':
            sys.exit(0)

    imagewin.focus_set()
    imagewin.bind("<KeyPress>", keypress)

    tkroot.mainloop()

