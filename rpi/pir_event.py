#!/usr/bin/env python

import time
import RPi.GPIO as GPIO

pir_pin = 7
sleeptime = 300

def motion_detected(pir_pin):
    print "Motion Detected!"

GPIO.setmode(GPIO.BCM)

GPIO.setup(pir_pin, GPIO.IN)

GPIO.add_event_detect(pir_pin, GPIO.RISING, callback=motion_detected)

while True:
    print "Sleeping for %d sec" % sleeptime
    time.sleep(sleeptime)
