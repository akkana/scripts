#!/usr/bin/env python

# Detect motion with a PIR hooked to a Raspberry Pi.

# Copyright 2014 by Akkana Peck. Share and enjoy under the GPLv2 or later.

import RPi.GPIO

class PIR:
    def __init__(self, pin):
        self.pin = pin

        RPi.GPIO.setmode(RPi.GPIO.BCM)
        RPi.GPIO.setup(self.pin, RPi.GPIO.IN)

    def poll(self):
        return RPi.GPIO.input(self.pin)

    def set_callback(self, cb):
        RPi.GPIO.add_event_detect(self.pin, RPi.GPIO.RISING, callback=cb)

if __name__ == "__main__":
    import time
    import sys

    def motion_detected(pin):
        print "Motion detected! (callback)"

    pin = 7
    use_callback = False

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "-c":
                use_callback = True
            else:
                pin = int(arg)

    pir = PIR(pin)

    if use_callback:
        pir.set_callback(motion_detected)

    while True:
        if use_callback:
            print "Sleeping a long time ..."
            time.sleep(300)

        else:
            if pir.poll():
                print "Motion detected! (poll)"
            time.sleep(1)
