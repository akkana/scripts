#!/usr/bin/env python

# Control 2 DC motors from a Raspberry Pi
# through a SN754410 quad half H-bridge chip.
# Copyright 2013 by Akkana Peck -- share and enjoy under the GPL v1 or later.

import RPi.GPIO as GPIO
import time

class PiMotor:
    def __init__(self, pwm, c0, c1):
        self.pwm_pin = pwm
        self.logic_pins = [c0, c1]
        self.pwm = None

        # We'll set these again in init_pins, but let's be sure:
        self.direc = None
        self.speed = 0

    def init_pins(self):
        '''Call GPIO.setup on all the pins we'll be using,
           and set the PWM pin to PWM mode.
        '''

        # Set both logic pins to output mode, initially LOW:
        for pin in self.logic_pins:
            print "Setting up", pin, "for output"
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0)

        # Set up the PWM pin:
        print "Setting up", self.pwm_pin, "for PWM"
        GPIO.setup(self.pwm_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pwm_pin, 50)
        self.pwm.start(0)

        # Initially we have no direction and no speed.
        self.direc = None
        self.speed = 0

    def stop(self):
        for pin in self.logic_pins:
            GPIO.output(pin, 0)
        if not self.pwm:
            return
        self.pwm.ChangeDutyCycle(0)
        self.pwm.stop()
        self.direc = None
        self.speed = 0
        print self.pwm_pin, "Stopped"

    def set_direction(self, direc):
        '''Change the current direction.
           None will set both pins to 0;
           0 will set the first pin to 1 and the second to 0,
           1 will do the reverse.
           Users shouldn't have to call this directly;
           use set_speed() with positive or negative values.
        '''
        if direc == self.direc:
            return

        self.pwm.ChangeDutyCycle(0)
        for pin in self.logic_pins:
            GPIO.output(pin, 0)

        if direc == 0 or direc == 1:
            print "Setting direction", direc
            GPIO.output(self.logic_pins[direc], 1)
        else:
            print "Direction none"

        self.direc = direc

        # Don't try to set the speed back to what it was before.
        # Put the responsibility on the caller to ramp up at a sane rate.

    def set_speed(self, speed):
        '''Set the speed, represented as a percentage of max
           (a number between 0 and 100).
           This is actually the duty cycle for the PWM pin.
        '''
        if not self.pwm:
            return
        self.speed = speed
        if speed == 0:
            self.set_direction(None)
        elif speed < 0:
            self.set_direction(1)
        else:
            self.set_direction(0)
        self.pwm.ChangeDutyCycle(abs(speed))

if __name__ == '__main__':
    # GPIO pins you can't use:
    # 14-15: used for serial console
    # 9-10: SPI0_MOSI and SPI0_MISO, no idea what that is
    # 23, 25: not used for anything but we can't use them anyway.
    # It looks like the pins we CAN use are:
    #    top row: 18, 23, 24, 25, 8, 7
    # bottom row: 4, 17, 22
    #motors = [ PiMotor(22, 9, 10), PiMotor(24, 7, 8) ]
    #motors = [ PiMotor(22, 23, 25), PiMotor(24, 7, 8) ]
    # Better for Pi plate, since it doesn't expose 7 and 8:
    motors = [ PiMotor(25, 23, 24), PiMotor(17, 21, 22) ]

    print "Cleaning up GPIO"
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)

    for m in motors:
        m.init_pins()

    # Drive straight:
    print "Driving straight"
    for m in motors:
        m.set_speed(30)
    time.sleep(2)

    # circle in one direction
    print "Circling"
    motors[0].set_speed(-20)
    motors[1].set_speed(80)
    time.sleep(2)

    # circle in the other direction
    print "Circling the other way"
    motors[0].set_speed(80)
    motors[1].set_speed(-20)
    time.sleep(2)

    # stop
    print "Stop"
    for m in motors:
        m.set_speed(0)
    time.sleep(2)

    # Back up
    print "Backing up"
    for m in motors:
        m.set_speed(-30)
    time.sleep(2)

    # stop
    print "Stop"
    for m in motors:
        m.stop()

    GPIO.cleanup()
