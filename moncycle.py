#!/usr/bin/env python3

# Cycle between connected monitors using xrandr.
# For instance, bind this to XF86Display in your window manager.

import sys
import subprocess

# Use monmon to detect connected and active monitors using python-xrandr.
# This saves needing to call xrandr and xrandr --listactivemonitors separately,
# which took twice as long.
import monmon

DEBUGFILE = open("/tmp/moncycle", "a")

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

# If only one monitor is connected, no-brainer.
if len(connected_mons) == 1:
    print("Only one connected monitor", file=DEBUGFILE)
    args = ["xrandr", "--output", connected_mons[0], "--auto"]
    print("calling", args, file=DEBUGFILE)
    subprocess.call(args)
    sys.exit(0)

# All monitors that are currently active:
active_mons = monmon.active_monitors()
if active_mons:
    # First monitors that's currently active
    active_mon = active_mons[0]
    print("Active monitors:", active_mons, file=DEBUGFILE)
else:
    active_mon = None
    print("No active monitors", file=DEBUGFILE)

# Nothing active? Use the first connected monitor.
nextindex = 0
# See if anything is active:
for i, mon in enumerate(connected_mons):
    if mon == active_mon:
        nextindex = (i+1) % len(connected_mons)
        break

args = [ "xrandr" ]

for i, mon in enumerate(connected_mons):
    if i == nextindex:
        args += [ "--output", mon, "--auto" ]
    else:
        args += [ "--output", mon, "--off" ]

print("Calling:", args, file=DEBUGFILE)
subprocess.call(args)

