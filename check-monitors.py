#!/usr/bin/env python3

# Check monitors and use xrandr to turn on the appropriate one(s).

# Ideally, this would be run from /etc/pm/sleep.d/check-monitors
# upon resume from suspend., something like this:
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


# Leave debugging info in a file of known location,
# because if it fails, you won't be able to see any error output,
# but maybe you can shell in and read what happened.
DEBUGFILE = '/tmp/check-monitors.out'


d = display.Display()
root = d.screen().root
resources = root.xrandr_get_screen_resources()._data
# from pprint import pprint
# print("resources:")
# pprint(resources)
# print("keys", resources.keys())

# Accessing modes sometimes makes outputs mysteriously disappear,
# so save outputs first.
outputs = resources['outputs']

# Build up a mode table. There's probably some clever IterTools construct
# that could do this in one line.
allmodes = {}
for m in resources['modes']:
    allmodes[m['id']] = '%dx%d' % (m['width'], m['height'])

# Loop over the outputs.
for output in outputs:
    data = d.xrandr_get_output_info(output,
                                    resources['config_timestamp'])._data

    if data['mm_width'] <= 0 or data['mm_height'] <= 0:
        # Not an actual monitor; I'm not sure what these are for
        # but they don't seem to have any useful info
        continue

    name = data['name']
    print("\n====", name)
    print(data)
    # print(data['modes'])

    # for m in data['modes']:
    #     print("Mode", m)
    print(", ".join([allmodes[m] for m in data['modes']]))

    # Figure out if it's cloned or extended, and its xinerama position
    # https://stackoverflow.com/questions/49136692/python-xlib-how-to-deterministically-tell-whether-display-output-is-in-extendi
    # which references https://www.x.org/wiki/Development/Documentation/HowVideoCardsWork/#index3h3
    try:
        crtcInfo = d.xrandr_get_crtc_info(data['crtc'],
                                          resources['config_timestamp'])
        # print(crtcInfo)
        x = crtcInfo.x
        y = crtcInfo.y
        print("   Size %dx%d   Position: (%d, %d)" % (crtcInfo.width,
                                                      crtcInfo.height,
                                                      crtcInfo.x, crtcInfo.y))
    except XError:
        print("    Xlib error")

