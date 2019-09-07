#!/usr/bin/env python3

# Check monitors and use xrandr to turn on the appropriate one(s).

# Ideally, this would be run from /etc/pm/sleep.d/check-monitors
# upon resume from suspend, something like this:
# case "${1}" in
#     resume|thaw)
#         check-monitors
#         ;;
# esac
# Unfortunately, /etc/pm/sleep.d/check-monitors isn't called reliably
# on resume, and neither is any other script. So it might be best
# to bind this to a key so that if you dock your laptop then wake it up,
# you can call it with a function key even if you can't see the screen
# to put focus in a window.
#


from Xlib import X, display
from Xlib.ext import randr
from Xlib.error import XError

import argparse
import sys


# Leave debugging info in a file of known location,
# because if it fails, you won't be able to see any error output,
# but maybe you can shell in and read what happened.
DEBUGFILE = '/tmp/check-monitors.out'

class XDisp:

    def __init__(self):
        # Display modes
        self.allmodes = {}

        # Monitor objects for all the connected monitors, indexed by name
        self.monitors = {}

        # width, height and xinerama x, y for all connected monitors,
        # indexed by name
        self.mon_geom = {}

        # If this is a laptop, the name of its native display
        self.laptop_screen = None


    def find_monitors(self):
        self.dpy = display.Display()
        self.root = self.dpy.screen().root
        print("root size", self.root.get_geometry())
        self.resources = self.root.xrandr_get_screen_resources()._data

        # Accessing modes sometimes makes outputs mysteriously disappear,
        # so save outputs first.
        outputs = self.resources['outputs']

        # Build up a mode table. There's probably some clever IterTools
        # construct that could do this in one line.
        for m in self.resources['modes']:
            self.allmodes[m['id']] = '%dx%d' % (m['width'], m['height'])

        # Loop over the outputs.
        for output in outputs:
            mondata = self.dpy.xrandr_get_output_info(
                output, self.resources['config_timestamp'])._data

            if mondata['mm_width'] <= 0 or mondata['mm_height'] <= 0:
                # Not an actual monitor; I'm not sure what these are for
                # but they don't seem to have any useful info
                continue

            name = mondata['name']
            self.monitors[name] = mondata
            if name.startswith('eDP') or name.startswith('LVDS'):
                self.laptop_screen = name
                print("laptop monitor:", name)

            # Figure out if it's cloned or extended, and its xinerama position
            # https://stackoverflow.com/questions/49136692/python-xlib-how-to-deterministically-tell-whether-display-output-is-in-extendi
            # which references https://www.x.org/wiki/Development/Documentation/HowVideoCardsWork/#index3h3
            # crtcInfo also includes rotation info but I'm not doing anything
            # with that since I don't personally use it.
            crtcInfo = self.dpy.xrandr_get_crtc_info(mondata['crtc'],
                                            self.resources['config_timestamp'])
            # print(crtcInfo)

            self.mon_geom[name] = {
                'x': crtcInfo.x,
                'y': crtcInfo.y,
                'width': crtcInfo.width,
                'height': crtcInfo.height,
                'mm_width': mondata['mm_width'],
                'mm_height': mondata['mm_height']
            }


    def print_monitor(self, mon, show_all_modes):
        if show_all_modes:
            print("\n%s:" % mon['name'])
            print(", ".join([self.allmodes[m] for m in mon['modes']]))

        geom = self.mon_geom[mon['name']]
        if self.laptop_screen == mon['name']:
            islaptop = "    **laptop"
        else:
            islaptop = ""
        print("Size: %4dx%4d   Position: (%4d, %4d)   mm: %d x %d%s"
              % (geom['width'], geom['height'], geom['x'], geom['y'],
                 geom['mm_width'], geom['mm_height'],
                 islaptop))


    def print_monitors(self, show_all_modes):
        for mname in self.monitors:
            self.print_monitor(self.monitors[mname], show_all_modes)


    def move_window(self, win, newx, newy):
        '''Move a window so it's visible on the screen.
        '''
        geom = win.get_geometry()
        if win.get_wm_name() == WINDOW_NAME:
            print("Current size", geom.width, geom.height)

            print('Moving Win')
            win.configure(x=newx, y=newy,
                          width=geom.width, height=geom.height,
                          # border_width=0,
                          stack_mode=Xlib.X.Above)
            dpy.sync()
        else:
            print("%s: %dx%d +%d+%d" % (win.get_wm_name(),
                                        geom.width, geom.height,
                                        geom.x, geom.y))


    def find_orphans(self):
        print("Trying to find orphans")

        window_ids = self.root.get_full_property(
            self.dpy.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType
        ).value
        for win_id in window_ids:
            win = self.dpy.create_resource_object('window', win_id)

            geom = win.get_geometry()

            print("%4dx%4d +%d+%d   %s" % (geom.width, geom.height,
                                           geom.x, geom.y,
                                           win.get_wm_name()))



    def move_orphan(self, win, geom, newx, newy):
        print("Moving %s from %d, %d. Current size %dx%d"
              % (win.name, geom.x, geom.y, geom.width, geom.height))

        win.configure(x=newx, y=newy,
                      width=geom.width, height=geom.height)
                      # border_width=0,
                      # stack_mode=Xlib.X.Above)
        dpy.sync()


if __name__ == '__main__':
    xdisp = XDisp()

    xdisp.find_monitors()

    parser = argparse.ArgumentParser(description="Check and change monitor connections")

    parser.add_argument('-s', "--switch", dest="switch", default=False,
                        action="store_true",
                        help="Switch which monitor(s) are connected")
    parser.add_argument('-a', "--allmodes", dest="show_all_modes",
                        default=False, action="store_true",
                        help="Show all modes allowed for each monitor")
    parser.add_argument('-o', "--orphans", dest="orphans", default=False,
                        action="store_true",
                        help="Find orphaned windows that are no longer visible")

    args = parser.parse_args(sys.argv[1:])

    if args.switch:
        print("Would switch!")

    elif args.orphans:
        xdisp.find_orphans()

    else:
        xdisp.print_monitors(args.show_all_modes)

