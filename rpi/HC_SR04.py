#!/usr/bin/env python

# Raspberry Pi driver for the HC-SR04 ultrasonic rangefinder.
# Copyright (C) 2014 Akkana Peck <akkana@shallowsky.com>>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

# Adapted from code by Matt Hawkins of RaspberryPi-Spy.co.uk
# Wire the circuit as shown in
# http://www.raspberrypi-spy.co.uk/2013/01/ultrasonic-distance-measurement-using-python-part-2/

import RPi.GPIO as GPIO
import time

class HC_SR04:
    def __init__(self, trigger=23, echo=24):
        self.GPIO_TRIGGER = trigger
        self.GPIO_ECHO    = echo

        # Use BCM instead of physical pin numbering:
        GPIO.setmode(GPIO.BCM)

        # Set trigger and echo pins as output and input
        GPIO.setup(self.GPIO_TRIGGER, GPIO.OUT)
        GPIO.setup(self.GPIO_ECHO, GPIO.IN)

        # Initialize trigger to low:
        GPIO.output(self.GPIO_TRIGGER, False)

    def measure_distance_cm(self, verbose=False):
        '''Measure a single distance, in cemtimeters.
        '''
        return self.measure_distance_in(verbose) * 2.54

    def measure_distance_in(self, verbose=False):
        '''Measure a single distance, in inches.
        '''
        if verbose:
            print "Sending trigger pulse ..."
        GPIO.output(self.GPIO_TRIGGER, True)
        time.sleep(0.00001)
        GPIO.output(self.GPIO_TRIGGER, False)
        if verbose:
            print "Waiting for ECHO to go low:"

        start = time.time()
        while GPIO.input(self.GPIO_ECHO) == 0:
            start = time.time()

        if verbose:
            print "Waiting for ECHO to go high:"
        stop = time.time()
        while GPIO.input(self.GPIO_ECHO) == 1:
            stop = time.time()
        if verbose:
            print "Got the echo."

        # Convert to inches:
        return (((stop - start) * 34300)/2)*0.393701

    def average_distance_in(self, samples=3, verbose=False):
        tot = 0.0
        for i in xrange(samples):
            tot += self.measure_distance_in(verbose)
            time.sleep(0.1)
        return tot / samples

if __name__ == '__main__':
    try:
        print "Initializing the rangefinder ..."
        rf = HC_SR04()
        while True:
            print "Distance: %.1f inches" % rf.average_distance_in(verbose=True)
            time.sleep(1)
    except KeyboardInterrupt:
        # User pressed CTRL-C: reset GPIO settings.
        print "Cleaning up ..."
        GPIO.cleanup()
