#!/usr/bin/env python3

import math

class Angle:
    """Stores one angle, in radians as a float.
       But if you set it to a value over 2*pi, or any integer,
       it will assume degrees and convert accordingly.

       NOTE: This isn't necessarily a good idea!
       But it's a good way to show how to use property getters/setters
       and operator overloading.
    """
    TWO_PI = math.pi * 2
    TO_RADIANS = math.pi / 180

    def __init__(self, val):
        self.radians = val

    @property
    def radians(self):
        print("Angle getter")
        return self._radians

    @radians.setter
    def radians(self, val):
        print("Angle setter")
        if val < Angle.TWO_PI:
            self._radians = val
        # Else assume degrees
        else:
            self._radians = val * Angle.TO_RADIANS

        # Make it positive and less than 2pi
        self._radians %= Angle.TWO_PI

        print(val, "->", self._radians)

    def __repr__(self):
        return "<Angle %.1f°>" % (self._radians / Angle.TO_RADIANS)

    def __add__(self, a):
        pass


if __name__ == '__main__':
    a1 = Angle(.4)
    a2 = Angle(310)
    a3 = Angle(-15)

    print("a1 (.4)  =", a1)
    print("a2 (310) =", a2)
    print("a3 (-15) =", a3)

    # print("a1 + a2:", a1 + a2)
    # print("a1 + a3:", a1 + a3)

