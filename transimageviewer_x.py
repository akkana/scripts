#!/usr/bin/env python3

import sys
import os

from PIL import Image

from Xlib import X, display, Xutil, Xatom
from Xlib.ext import shape


class XImageWindow():
    def __init__(self, imgname, opacity=1, magnification=100):
        self.imgname = sys.argv[1]
        self.img = Image.open(self.imgname)

        if magnification != 100:
            newwidth = self.img.width * magnification / 100
            newheight = self.img.height * magnification / 100
            self.img = self.img.resize(newwidth, newheight)

        self.opacity = opacity/100.

        self.dpy = display.Display()
        self.screen = self.dpy.screen()

        self.width = self.img.width
        self.height = self.img.height
        x0 = 100
        y0 = 100

        self.win = self.screen.root.create_window(
            x0, y0, self.width, self.height, 0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            colormap=X.CopyFromParent,
            event_mask = X.StructureNotifyMask | X.ExposureMask
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

        # Would be nice to add the clickthrough input shapemask here,
        # but it doesn't work if added this early.

        self.win.map()

    def add_xlib_clickthrough(self):
        """Attempt to add clickthrough to the window,
           using Xlib's SHAPE extension.
        """
        if not self.dpy.has_extension('SHAPE'):
            sys.stderr.write('%s: server does not have SHAPE extension\n'
                             % os.path.basename(sys.argv[0]))
            return

        # create a pixmap for the input shape
        geom = self.win.get_geometry()

        input_pm = self.screen.root.create_pixmap(geom.width, geom.height, 1)
        gc = input_pm.create_gc(foreground=1, background=0)
        input_pm.fill_rectangle(gc, 0, 0, geom.width, 20)
        gc.change(foreground=0)
        input_pm.fill_rectangle(gc, 0, 20, geom.width, geom.height-20)

        # SO options are Intersect, Invert, Set, Subtract, Union
        # SK options are Bounding, Clip, Input
        # See https://www.x.org/releases/X11R7.7/doc/libXext/shapelib.html
        self.win.shape_mask(shape.SO.Set, shape.SK.Input, 0, 0, input_pm)
        gc.free()

    def mainloop(self):
        while True:
            e = self.dpy.next_event()
            # print(e)
            if e.type == X.ConfigureNotify or e.type == X.Expose:
                gc = self.screen.root.create_gc(
                    foreground=self.screen.white_pixel,
                    background=self.screen.black_pixel)

                self.win.put_pil_image(gc, 0, 0, self.img)

                gc.free()

                if self.opacity < 1:
                    self.add_xlib_clickthrough()

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
                        help='opacity (percent: default 100)')
    parser.add_argument('-m', '--magnify', type=int, default=100,
                        help='magnification factor (percent: default 100)')
    args = parser.parse_args(sys.argv[1:])

    imgwin = XImageWindow(args.imgfile, opacity=args.opacity,
                          magnification=args.magnify)
    try:
        imgwin.mainloop()
    except KeyboardInterrupt:
        print("Bye")
        sys.exit(0)
