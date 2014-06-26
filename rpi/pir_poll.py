#!/usr/bin/env python

import time
import RPi.GPIO as GPIO

pir_pin = 7
sleeptime = 1

GPIO.setmode(GPIO.BCM)

GPIO.setup(pir_pin, GPIO.IN)

while True:
    if GPIO.input(pir_pin):
        print "Motion detected!"
    time.sleep(sleeptime)
