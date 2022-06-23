#!/usr/bin/env python3

import sys
import os

from PIL import Image

from Xlib import X, display, Xutil
from Xlib.ext import shape


imgname = sys.argv[1]
img = Image.open(imgname)

dpy = display.Display()
screen = dpy.screen()

winwidth = img.width
winheight = img.height
x0 = 100
y0 = 100

gc = screen.root.create_gc(foreground=screen.white_pixel,
                                background=screen.black_pixel)

win = screen.root.create_window(
    x0, y0, winwidth, winheight, 0,
    screen.root_depth,
    X.InputOutput,
    X.CopyFromParent,
    colormap=X.CopyFromParent,
    event_mask = X.StructureNotifyMask
)

win.set_wm_name(imgname)

WM_DELETE_WINDOW = dpy.intern_atom('WM_DELETE_WINDOW')
WM_PROTOCOLS = dpy.intern_atom('WM_PROTOCOLS')
win.set_wm_protocols([WM_DELETE_WINDOW])

gc = win.create_gc(foreground=screen.white_pixel,
                   background=screen.black_pixel)

win.map()

while True:
    e = dpy.next_event()
    # print(e)
    if e.type == X.ConfigureNotify:
        win.put_pil_image(gc, 0, 0, img)
        dpy.flush()
        continue

    # Window has been destroyed, quit
    if e.type == X.DestroyNotify:
        sys.exit(0)

    if e.type == X.ClientMessage:
        if e.client_type == WM_PROTOCOLS:
            fmt, data = e.data
            if fmt == 32 and data[0] == WM_DELETE_WINDOW:
                sys.exit(0)

