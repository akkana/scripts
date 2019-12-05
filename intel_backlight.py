#!/usr/bin/env python3

# Can you believe there's no standard program in Debian/Ubuntu
# to adjust an Intel backlight? Sheesh.

# This script maps everything to 0-100.

#  echo 3000 | sudo tee /sys/class/backlight/intel_backlight/brightness
# /sys/class/backlight/intel_backlight/max_brightness

import sys
import argparse

def get_max_brightness():
    with open('/sys/class/backlight/intel_backlight/max_brightness') as fp:
        return int(fp.read().strip())

try:
    max_bright = get_max_brightness()
except:
    sys.exit("Can't read max brightness")

def get_brightness():
    print("get_brightness")
    with open('/sys/class/backlight/intel_backlight/brightness') as fp:
        return float(fp.read().strip()) * 100. / max_bright

def set_brightness(newval):
    print("set_brightness", newval)
    newval = int(newval * max_bright / 100. + .5)
    with open('/sys/class/backlight/intel_backlight/brightness', 'w') as fp:
        print("Writing", newval)
        print(newval, file=fp);

def change_brightness(incr):
    bright = get_brightness()
    if bright < 7:
        incr /= 10
    print("change_brightness from", bright, "by", incr)
    bright += incr
    if bright > 100:
        bright = 100
    if bright < 0:
        bright = .01
    set_brightness(bright)


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print(get_brightness())
        sys.exit(0)

    for arg in sys.argv[1:]:
        if arg.startswith('+') or arg.startswith('-'):
            change_brightness(float(arg))
        else:
            set_brightness(float(arg))

