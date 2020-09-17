#!/usr/bin/env python3

# Cycle between connected monitors using xrandr.
# For instance, bind this to XF86Display in your window manager.

# XXX Need to change desktop/screen resolution too.
# When cycling to a new monitor, also need -s newwxnewh

# In dire debugging circumstances:
# import os
# os.system("xrandr >/tmp/xrandr.out")

import sys
import subprocess

# Use monmon to detect connected and active monitors using python-xrandr.
# This saves needing to call xrandr and xrandr --listactivemonitors separately,
# which took twice as long.
import monmon

# Order to prefer monitors. If connected to an external display,
# activate it first in preference to the built-in monitor.
preferred_order = [ 'HDMI', 'DP', 'VGA', 'eDP', 'LVDS' ]

def find_in_preferred_list(mon_name, start_from=0):
    """Return the first monitor type (e.g. 'HDMI') that matches mon_name,
       or None.
    """
    if start_from > 0:
        thelist = preferred_order + preferred_order[:start_from]
    else:
        thelist = preferred_order
    for t in preferred_order[start_from:]:
        if t in mon_name:
            return t
    return None

DEBUGFILE = open("/tmp/moncycle.out", "a")

print("==== moncycle ===============", file=DEBUGFILE)

monmon = monmon.MonMon()
monmon.find_monitors()

# Monitors that are physically connected (a dict of dicts):
connected_mons = monmon.connected_monitors()

# If there are no connected monitors, big trouble.
if not connected_mons:
    print("No monitors connected! Bailing.", file=DEBUGFILE)
    sys.exit(1)

print("Connected monitors:", connected_mons, file=DEBUGFILE)

def mon_connect_str(mondata):
    """Given a monmon mondata dict, return a list of xrandr
       connection arguments specifying the preferred geometry
       if any, otherwise --auto.
    """
    if "preferred" in mondata:
        return [ "--output", mondata["name"],
                 "--mode", mondata["preferred"],
                 "-s", mondata["preferred"] ]
    return [ "--output", mondata["name"], "--auto" ]

# If only one monitor is connected, no-brainer.
# Except no, not really. Also need -s resolution.
if len(connected_mons) == 1:
    if monmon.mon_geom:
        # Sometimes the single monitor doesn't get a geometry,
        # but we need to try to connect to it anyway.
        geom = monmon.mon_geom[connected_mons[0]]
        if geom:
            geomstr = "%dx%d" % (geom['width'], geom['height'])
    args = ["xrandr"] + mon_connect_str(monmon.monitors[connected_mons[0]])
    print("Calling:", args, file=DEBUGFILE)
    subprocess.call(args)
    sys.exit(0)

# Two or more monitors are connected.
# If one is active, switch the display to the next one in the preferred list.
# If none are active, turn on the most preferred type.
active_mons = monmon.active_monitors()
if active_mons:
    print("Active monitors:", active_mons, file=DEBUGFILE)
    active_mon = active_mons[0]

else:
    print("No active monitors", file=DEBUGFILE)
    active_mon = None

# Use the first connected monitor (with the currently active monitor
# excluded), in order of preference.
new_mon = None
for montype in preferred_order:
    for mon in connected_mons:
        if montype in mon and mon != active_mon:
            new_mon = mon
            break

if not new_mon:
    print("Connected monitors are", ' '.join(connected_mons))
    print("None of them match any of", ' '.join(preferred_order))
    sys.exit(1)

args = [ "xrandr" ]
geomstr = None

for mon in connected_mons:
    if mon == new_mon:
        args += mon_connect_str(monmon.monitors[mon])

    else:
        args += [ "--output", mon, "--off" ]

print("Calling:", args, file=DEBUGFILE)
subprocess.call(args)
sys.exit(0)

