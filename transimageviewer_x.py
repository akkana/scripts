#!/usr/bin/env python3

import sys
import os

from PIL import Image

from Xlib import X, display, Xutil, Xatom
from Xlib.ext import shape


class XImageWindow():
    def __init__(self, imgname, opacity=1):
        self.imgname = sys.argv[1]
        self.img = Image.open(self.imgname)

        self.opacity = opacity/100.

        self.dpy = display.Display()
        self.screen = self.dpy.screen()

        self.width = self.img.width
        self.height = self.img.height
        x0 = 100
        y0 = 100

        gc = self.screen.root.create_gc(foreground=self.screen.white_pixel,
                                        background=self.screen.black_pixel)

        self.win = self.screen.root.create_window(
            x0, y0, self.width, self.height, 0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            colormap=X.CopyFromParent,
            event_mask = X.StructureNotifyMask
        )

        self.win.set_wm_name(self.imgname)

        self.WM_DELETE_WINDOW = self.dpy.intern_atom('WM_DELETE_WINDOW')
        self.WM_PROTOCOLS = self.dpy.intern_atom('WM_PROTOCOLS')
        self.win.set_wm_protocols([self.WM_DELETE_WINDOW])

        # Set window opacity. change_property expects an array containing
        # a single 32-bit hex number, e.g.0x7F7F7F7F  would be 50%,
        # 0xFFFFFFFF is fully opaque.
        onebyte = int(0xff * self.opacity)
        fourbytes = onebyte | (onebyte << 8) | (onebyte << 16) | (onebyte << 24)
        XA_NET_WM_WINDOW_OPACITY = \
            self.dpy.intern_atom('_NET_WM_WINDOW_OPACITY')
        self.win.change_property(self.dpy.get_atom('_NET_WM_WINDOW_OPACITY'),
                                 Xatom.CARDINAL, 32, [fourbytes])

        self.gc = self.win.create_gc(foreground=self.screen.white_pixel,
                                     background=self.screen.black_pixel)

        self.win.map()

    def mainloop(self):
        while True:
            e = self.dpy.next_event()
            # print(e)
            if e.type == X.ConfigureNotify:
                self.win.put_pil_image(self.gc, 0, 0, self.img)
                self.dpy.flush()
                continue

            # Window has been destroyed, quit
            if e.type == X.DestroyNotify:
                sys.exit(0)

            if e.type == X.ClientMessage:
                if e.client_type == self.WM_PROTOCOLS:
                    fmt, data = e.data
                    if fmt == 32 and data[0] == self.WM_DELETE_WINDOW:
                        sys.exit(0)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Show an image transparently, with click-through")
    parser.add_argument('imgfile', help='Image to show')
    parser.add_argument('-o', '--opacity', type=int, default=100,
                        help='opacity (percent: default 50)')
    args = parser.parse_args(sys.argv[1:])

    imgwin = XImageWindow(args.imgfile, opacity=args.opacity)
    imgwin.mainloop()
