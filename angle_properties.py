#!/usr/bin/env python3

# A cheatsheet for how to use Python properties and operator overloading.
# Not intended for use in actual programs, though you're welcome to do
# so if you want. No license, public domain.

import math

class Angle:
    """Stores one angle.
       Internally it's stored in radians as a float,
       but you can set or get it with a.radians or a.degrees.

       If you set it in the constructor to a value over 2*pi,
       without specifying radians or degrees,
       it will assume degrees and convert accordingly.

       NOTE: This isn't necessarily a good idea!
       But it's a good way to show how to use property getters/setters
       and operator overloading.
    """
    TWO_PI = math.pi * 2
    TO_RADIANS = math.pi / 180

    def __init__(self, *args, **kwargs):
        """Pass in the value of the angle, as radians=r or degrees=d.
           If you just pass in a number, Angle will try to guess
           based on whether it's over 2*pi.

           Usage examples:
             Angle(radians=math.pi)
             Angle(degrees = 45)
             Angle(1.44)
        """
        if 'radians' in kwargs:
            self.radians = kwargs['radians']
        elif 'degrees' in kwargs:
            self.degrees = kwargs['degrees']
        elif len(args) == 1:
            if abs(args[0]) < Angle.TWO_PI:
                self.radians = args[0]
            else:
                self.degrees = args[0]
        else:
            raise RuntimeError("Angle: Can't make sense of arguments")

    def constrain_radians(self):
        """Make the angle positive and less than 2pi"""
        self._radians %= Angle.TWO_PI

        # while self._radians < 0:
        #     self._radians += Angle.TWO_PI
        # while self._radians > Angle.TWO_PI:
        #     self._radians -= Angle.TWO_PI

    @property
    def radians(self):
        return self._radians

    @radians.setter
    def radians(self, val):
        self._radians = val
        self.constrain_radians()
        print("radians setter", val, "->", self._radians)

    @property
    def degrees(self):
        return self._radians / Angle.TO_RADIANS

    @degrees.setter
    def degrees(self, val):
        print("degrees_setter", val)
        self.radians = val * Angle.TO_RADIANS

    def __repr__(self):
        return "<Angle %.1f°>" % (self.degrees)

    def __add__(self, a):
        pass


if __name__ == '__main__':
    # Values to be passed as non-keyword args
    vals = [.4, 310, -15, 400]
    # and the degrees that should result from each
    test_angles = [22.918, 310, 345, 40]

    def too_different(x, y):
        return abs(x - y) > .01

    angles = []
    for (v, ta) in zip(vals, test_angles):
        print("\n==== Setting", v)
        ang = Angle(v)
        angles.append(ang)
        if too_different(ang.degrees, ta):
            print("**************", v, "->", ang.degrees, "should be", ta)
        else:
            print(v, "->", ang)

    # print("a1 (.4)  =", a1)
    # print("a2 (310) =", a2)
    # print("a3 (-15) =", a3)

    # print("a1 + a2:", a1 + a2)
    # print("a1 + a3:", a1 + a3)

