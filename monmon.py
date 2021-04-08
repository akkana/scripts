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

from ewmh import EWMH

import argparse
import sys


# Leave debugging info in a file of known location,
# because if it fails, you won't be able to see any error output,
# but maybe you can shell in and read what happened.
DEBUGFILE = open("/tmp/monmon.out", "a")

class MonMon:

    def __init__(self):
        # Display modes
        self.allmodes = {}

        # Monitor objects for all the connected monitors, indexed by name
        self.monitors = {}

        # width, height and xinerama x, y for all active monitors,
        # indexed by name
        self.mon_geom = {}

        # If this is a laptop, the name of its native display
        self.laptop_screen = None

        # A list of [ (win, geom) ] for all windows on screen
        self.allwindows = []


    def find_monitors(self):
        self.dpy = display.Display()
        self.root = self.dpy.screen().root
        self.resources = self.root.xrandr_get_screen_resources()._data
        self.ewmh = EWMH()

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
                print("Not real monitor, skipping", file=DEBUGFILE)
                continue

            try:
                prefmode = mondata['modes'][mondata['num_preferred']] - 1
                mondata['preferred'] = self.allmodes[prefmode]
            except:
                print("Couldn't get", mondata['name'], "preferred modes",
                      file=DEBUGFILE)

            name = mondata['name']
            self.monitors[name] = mondata
            if name.startswith('eDP') or name.startswith('LVDS'):
                self.laptop_screen = name

            # Get the geometry, and Figure out if it's cloned or extended,
            # and its xinerama position
            # https://stackoverflow.com/questions/49136692/python-xlib-how-to-deterministically-tell-whether-display-output-is-in-extendi
            # which references https://www.x.org/wiki/Development/Documentation/HowVideoCardsWork/#index3h3
            # crtcInfo also includes rotation info but I'm not doing anything
            # with that since I don't personally use it.
            try:
                crtcInfo = self.dpy.xrandr_get_crtc_info(mondata['crtc'],
                                           self.resources['config_timestamp'])

                self.mon_geom[name] = {
                    'x': crtcInfo.x,
                    'y': crtcInfo.y,
                    'width': crtcInfo.width,
                    'height': crtcInfo.height,
                    'mm_width': mondata['mm_width'],
                    'mm_height': mondata['mm_height']
                }

            except XError:
                # If get_crtc_info fails it means that the monitor is
                # connected but not active.
                print("No crtc info", file=DEBUGFILE)
                pass


    def active_monitors(self):
        """List monitors xrandr is actually using"""
        active = []
        for mname in self.monitors:
            if mname in self.mon_geom:
                active.append(mname)
        return active


    def inactive_monitors(self):
        """List monitors that are connected but not being used"""
        inactive = []
        for mname in self.monitors:
            if mname not in self.mon_geom:
                inactive.append(mname)
        return inactive


    def connected_monitors(self):
        """List all connected monitors"""
        return list(self.monitors.keys())


    def print_monitor(self, mon, show_all_modes):
        """Print a connected monitor.
        """
        if show_all_modes:
            print("\n%s:" % mon['name'])
            print(", ".join([self.allmodes[m] for m in mon['modes']]))

        try:
            geom = self.mon_geom[mon['name']]
            if self.laptop_screen == mon['name']:
                islaptop = "    **laptop"
            else:
                islaptop = ""
            print("%s: %4dx%4d   Position: (%4d, %4d)   mm: %d x %d%s"
                  % (mon['name'],
                     geom['width'], geom['height'], geom['x'], geom['y'],
                     geom['mm_width'], geom['mm_height'],
                     islaptop))

        except KeyError:
            print("%s: Inactive" % mon['name'])


    def print_monitors(self, show_all_modes, list_monitors):
        for mname in self.monitors:
            if list_monitors:
                print(mname)
            else:
                self.print_monitor(self.monitors[mname], show_all_modes)


    def move_window(self, win, newx, newy):
        """Move a window so it's visible on the screen.
        """
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


    def find_all_windows(self):
        def topframe(client):
            frame = client
            while frame.query_tree().parent != self.ewmh.root:
                frame = frame.query_tree().parent
            return frame

        for client in self.ewmh.getClientList():
            geom = topframe(client).get_geometry()
            self.allwindows.append((client, geom))


    def print_all_windows(self):
        if not self.allwindows:
            self.find_all_windows()

        for win, geom in self.allwindows:
            name, classname = win.get_wm_class()
            print("%4d x %4d   +%4d + %4d   %s: %s" % (geom.width,
                                                       geom.height,
                                                       geom.x, geom.y,
                                                       name,
                                                       win.get_wm_name()))


    def is_visible(self, x, y):
        """Is the point x, y currently visible? That is, is there
           currently a connected screen that is showing that point?
        """
        x_visible = False
        y_visible = False
        for mname in self.mon_geom:
            geom = self.mon_geom[mname]

            # Is x visible?
            if x > geom['x'] and x < geom['x'] + geom['width']:
                x_visible = True

            # Is y visible?
            if y > geom['y'] and y < geom['y'] + geom['height']:
                y_visible = True

            if x_visible and y_visible:
                print("%d, %d visible on monitor %s" % (x, y, mname))
                return True

        return False


    def find_orphans(self):
        print("Trying to find orphans")

        if not self.allwindows:
            self.find_all_windows()

        # A safe place to move orphans, on the laptop screen or, otherwise,
        # the first connected display.
        if self.laptop_screen:
            safegeom = self.mon_geom[self.laptop_screen]
        else:
            # Just pick the first one, understanding that dicts have no "first"
            safegeom = self.mon_geom[self.mon_geom.keys()[0]]
        safe_x = safegeom['x'] + 25
        safe_y = safegeom['y'] + 25

        for win, geom in self.allwindows:
            name, classname = win.get_wm_class()

            if not self.is_visible(geom.x, geom.y):
                self.move_orphan(win, geom, safe_x, safe_y)


    def move_orphan(self, win, geom, newx, newy):
        print("Moving %s from %d, %d. Current size %dx%d"
              % (win.get_wm_name(), geom.x, geom.y, geom.width, geom.height))

        win.configure(x=newx, y=newy,
                      width=geom.width, height=geom.height)
                      # border_width=0,
                      # stack_mode=Xlib.X.Above)
        self.dpy.sync()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Check and change monitor connections")

    parser.add_argument('-a', "--allmodes", dest="show_all_modes",
                        default=False, action="store_true",
                        help="Show all modes allowed for each monitor")
    parser.add_argument('-d', "--debug", dest="debug",
                        default=False, action="store_true",
                        help="Debug mode: print comments to stdout, not log file")
    parser.add_argument('-w', "--allwindows", dest="show_all_windows",
                        default=False, action="store_true",
                        help="Show all existing top-level windows")
    parser.add_argument('-o', "--orphans", dest="orphans", default=False,
                        action="store_true",
                        help="Find orphaned windows that are no longer visible, and move them back onscreen")
    parser.add_argument("--monlist", dest="list_monitors",
                        default=False, action="store_true",
                        help="Provide an easily parseable list of available monitors")

    args = parser.parse_args(sys.argv[1:])

    if args.debug:
        DEBUGFILE = sys.stderr
    else:
        DEBUGFILE = open('/tmp/check-monitors.out', 'w')

    monmon = MonMon()

    monmon.find_monitors()

    if args.show_all_windows:
        monmon.print_all_windows()

    elif args.orphans:
        monmon.find_orphans()

    else:
        monmon.print_monitors(args.show_all_modes, args.list_monitors)

# XXX It would be nice to be able to enable and disable monitors with this
# program. However, there's no documentation for how to do that with
# python randr, and no one anywhere seems to have even tried.
# Some vaguely relevant docs:
# https://www.x.org/wiki/Development/Documentation/HowVideoCardsWork/
# https://cgit.freedesktop.org/xorg/proto/randrproto/tree/randrproto.txt
