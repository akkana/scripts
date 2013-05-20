#!/usr/bin/env python

# Choose a pin that's exposed on the Pi Plate and not used by motors:
# Available are: 4 and 18.

# Thanks to http://raspi.tv/2013/how-to-use-interrupts-with-python-on-the-raspberry-pi-and-rpi-gpio-part-2

# Some rangefinder-and-PWM-specific pages:
# http://www.raspberrypi.org/phpBB3/viewtopic.php?t=36593&p=311048
# http://www.raspberrypi-spy.co.uk/2012/12/ultrasonic-distance-measurement-using-python-part-1/
# http://www.raspberrypi-spy.co.uk/2013/01/ultrasonic-distance-measurement-using-python-part-2/

# In practice, number varies between .027 and .049
# Spec sheet says it's 147uS per inch, at least for one maxbotix
# (may or may not be the same model as mine).

import RPi.GPIO as GPIO
import sys
import signal
import time

# In the example, cleanup was set up as a try/except KeyboardInterrupt.
# But the KeyboardInterrupt exception isn't reliable in threaded
# programs (even when the threads are in the backend, e.g. we
# don't know what wait_for_edge() is doing, but apparently it's
# doing something that breaks KeyboardInterrupt.
# More analysis at
# http://stackoverflow.com/questions/4606942/why-cant-i-handle-a-keyboardinterrupt-in-python
#
# So instead, define a signal handler and clean up that way.
# Curiously, with this approach we still get a Python traceback
# for the KeyboardInterrupt -- maybe it's coming from something
# inside wait_for_edge -- but the handler fires anyway.
def signal_handler(signal, frame):
    print 'You pressed Ctrl+C! Cleaning up.'
    GPIO.cleanup()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def read_distance(rfpin):
    '''Read the distance from the rangefinder, using PWM.
    Empirically, the HIGH time varies between 3 (at long distance)
    and 50 (at very short distance).
    LOW time doesn't have any obvious correlation with distance.
    This isn't at all what the documentation says -- it's supposed
    to stay high while it waits for the return pulse, so long distances
    should correlate with long times.
    '''

    # Read 10 times and average the readings:
    tot = 0
    numreadings = 6
    for i in range(numreadings):
        try:
            GPIO.wait_for_edge(rfpin, GPIO.RISING)
            rise = time.time()

            GPIO.wait_for_edge(rfpin, GPIO.FALLING)
            fall = time.time()
            elapsed = fall - rise

            GPIO.wait_for_edge(rfpin, GPIO.RISING)
            rise2 = time.time()

            #print i, elapsed, rise2 - fall
            print i, (fall - rise)*1000, (rise2 - fall)*1000

            tot += elapsed

        except RuntimeError:
            # This can get Error #3 waiting for edge
            print "Error waiting for edge"

    # tot / numreadings is in seconds.
    return tot / numreadings * 1000000 / 147

if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)

    rfpin = 18
    GPIO.setup(rfpin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    while True:
        dist = read_distance(rfpin)
        print "Distance:", dist
        sys.stdout.flush()
        time.sleep(2)

    GPIO.cleanup()
