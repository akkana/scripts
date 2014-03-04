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

import RPi.GPIO as GPIO
import time

GPIO_TRIGGER = 23
GPIO_ECHO    = 24

def init_HC_SR04():
    '''Call this once at the beginning of the script
       before measuring any distances.
    '''
    # Use BCM instead of physical pin numbering:
    GPIO.setmode(GPIO.BCM)

    # Set trigger and echo pins as output and input
    GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
    GPIO.setup(GPIO_ECHO, GPIO.IN)

    # Initialize trigger to low:
    GPIO.output(GPIO_TRIGGER, False)

def measure_distance_cm():
    '''Measure a single distance, in cemtimeters.
    '''
    GPIO.output(GPIO_TRIGGER, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
    start = time.time()

    while GPIO.input(GPIO_ECHO) == 0:
        start = time.time()

    while GPIO.input(GPIO_ECHO) == 1:
        stop = time.time()

    # Convert to centimeters:
    return ((stop - start) * 34300)/2

def average_distance(samples=3):
    tot = 0.0
    for i in xrange(samples):
        tot += measure_distance()
        time.sleep(0.1)
    return tot / samples

if __name__ == '__main__':
    try:
        init_HC_SR04()
        while True:
            print "Distance: %.1f" % average_distance()
            time.sleep(1)
    except KeyboardInterrupt:
        # User pressed CTRL-C: reset GPIO settings.
        print "Cleaning up ..."
        GPIO.cleanup()
