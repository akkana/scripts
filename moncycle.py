#!/usr/bin/env python3

# Cycle between connected monitors using xrandr.
# For instance, bind this to XF86Display in your window manager.

import sys
import subprocess

DEBUGFILE = open("/tmp/moncycle", "a")

print("===============", file=DEBUGFILE)

# The types of monitors to care about, in the order we care.
montypes = [ "eDP", "HDMI" ]
# This will have keys name (str), connected (bool), active (bool).
monitors = {}


# Monitors that are physically connected:
proc = subprocess.Popen(["xrandr"], stdout=subprocess.PIPE)
for line in proc.stdout:
    if not line:
        continue
    line = line.decode('utf-8')
    if line[0] == ' ':
        continue
    # Now line should look something like:
    # HDMI-1 connected 1920x1200+0+0 (normal left inverted right x axis y axis) 518mm x 324mm\n

    words = line.split()
    if words[1] != 'connected':
        continue

    # Now it's a line for a physically connected monitor.
    for montype in montypes:
        if montype in words[0]:
            monitors[montype] = {
                'name': words[0],
                'connected': True,
                'active': False
            }

print("Connected monitors:", monitors, file=DEBUGFILE)

# But which monitors are actually active? That's not easy to tell from
# the normal xrandr output. You can tell it from xrandr --listmonitors
# or --listactivemonitors, which are mentioned in xrandr --help
# but not in man xrandr; in practice they both list active monitors,
# not connected monitors (hooray for commands with predictable,
# easily parseable output! not.) It would be nice to be able to
# get both in one command, because xrandr is quite slow, requiring
# several seconds for each invocation.

proc = subprocess.Popen(["xrandr", "--listactivemonitors"],
                        stdout=subprocess.PIPE)
for line in proc.stdout:
    line = line.decode('utf-8')
    if line.startswith("Monitors:"):
        continue
    words = line.split()
    # The monitor name starts with a + for some unknown reason, so strip that.
    mon_name = words[1][1:]

    for montype in montypes:
        if montype in mon_name:
            # Only interested in monitors that are connected.
            # The active list may include other monitors that USED
            # to be connected, which explicitly shouldn't be included.
            if montype in monitors:
                monitors[montype]['active']  = True
            # else:
            #     print("%s is listed as active but isn't connected" % mon_name,
            #             file=DEBUGFILE)

print("Active monitors:", monitors, file=DEBUGFILE)

# Whew. Now we have the two monitor lists.
# Cycle through each of the monitor types.
# XXX Eventually, add a mode where all monitors are active.

# If only one monitor is connected, no-brainer.
if len(monitors) == 1:
    firstmon = monitors[next(iter(monitors))]
    args = ["xrandr", "--output", firstmon['name'], "--auto"]

else:
    # If more than one connected, cycle.
    for i, montype in enumerate(montypes):
        if monitors[montype]['active']:
            nexttype = montypes[(i + 1) % len(montypes)]
            args = ["xrandr",
                    "--output", monitors[nexttype]['name'], "--auto",
                    "--output", monitors[montype]['name'], "--off"]
print("Calling:", args, file=DEBUGFILE)
subprocess.call(args)

