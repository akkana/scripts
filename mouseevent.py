#!/usr/bin/env python

# Read mouse events if X isn't running -- for instance, on a Raspberry Pi.
# Needs root, or at least read access to /dev/input/*

import evdev
import select
import time
import sys

class MouseReader:
    def __init__(self):
        self.mousedevice = None
        devices = map(evdev.InputDevice, evdev.list_devices())
        for dev in devices:
            caps = dev.capabilities()
            keys = caps.keys()
            # 1L is "EV_KEY" events (mouse buttons);
            # 2L is 'EV_REL' for the wheel.
            if evdev.ecodes.EV_KEY in keys and evdev.ecodes.EV_REL in keys:
                if evdev.ecodes.BTN_LEFT in caps[evdev.ecodes.EV_KEY] and \
                        evdev.ecodes.BTN_RIGHT in caps[evdev.ecodes.EV_KEY] \
                        and evdev.ecodes.REL_WHEEL in caps[evdev.ecodes.EV_REL]:
                       # Quacks like a mouse. Use it.
                    self.mousedevice = dev
                    return

        if not mousedevice:
            print "Didn't see a mouse device"

    def pval(self, code, val):
        try:
            codes = evdev.ecodes.BTN[code]
            if type(codes) is list:
                print codes[0],
            else:
                print codes,
        except:
            try:
                print evdev.ecodes.REL[code],
            except:
                print "Unknown code", code

        if val == 1:
            if code == evdev.ecodes.REL_WHEEL:
                print "scroll up"
            else:
                print "press"
        elif val == 0:
            print "release"
        elif val == -1:
            print "scroll down"
        else:
            print "unknown value", val

    def read_mouse(self, timeout=None):
        '''Returns an evdev event.
           timeout is specified in floating-point seconds.
           timeout=None will block until there's something to read.
        '''
        r,w,x = select.select([self.mousedevice], [], [], timeout)
        events = []
        for event in self.mousedevice.read():
            # event.value will be 1 for button down, 0 for button up,
            # 1 for wheel up, -1 for wheel down.
            if event.code in (evdev.ecodes.REL_WHEEL,
                              evdev.ecodes.BTN_LEFT,
                              evdev.ecodes.BTN_RIGHT,
                              evdev.ecodes.BTN_MIDDLE):
                events.append((event.code, event.value))
        return events

if __name__ == '__main__':
    mousereader = MouseReader()
    if not mousereader.mousedevice:
        sys.exit(1)

    while True:
        try:
            events = mousereader.read_mouse(.1)
            for ev in events:
                mousereader.pval(ev[0], ev[1])
        except IOError:
            pass

        print "\n==================\nSleeping"
        time.sleep(5)
