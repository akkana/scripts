#!/usr/bin/python
"""Demonstrate harmonic synthesis in Python using NumPy.

Originally from:
    http://osdir.com/ml/culture.people.kragen.hacks/2007-11/msg00000.html
and https://mail.python.org/pipermail/tutor/2009-January/066173.html

Unrelated, but also check out:
play -n synth pl G2 pl B2 pl D3 pl G3 pl D4 pl G4 \
               delay 0 .05 .1 .15 .2 .25 remix - fade 0 4 .1 norm -1
you can use # and b for sharps/flats, e.g. G#4 is a high G sharp.
Check the SoX(1) man page for more fun examples.

"""

import pygame, pygame.sndarray
import numpy
import time, random

sample_rate = 44100

def sine_array_onecycle(hz, peak):
    "Compute one cycle of an N-Hz sine wave with given peak amplitude."
    length = sample_rate / float(hz)
    omega = numpy.pi * 2 / length
    xvalues = numpy.arange(int(length)) * omega
    return (peak * numpy.sin(xvalues)).astype(numpy.int16)

def sine_array(hz, peak, n_samples = sample_rate):
    """Compute N samples of a sine wave with given frequency and peak amplitude.

    Defaults to one second."""
    return numpy.resize(sine_array_onecycle(hz, peak), (n_samples,))

def second_harmonic(hz):
    "Compute a wave with a strong second harmonic."
    return sine_array(hz, 16384) + sine_array(hz * 2, 16384)

def brass(hz):
    "Compute a sound with some odd harmonics. Doesn't really sound brassy."
    return sum([sine_array(hz, 4096),
                sine_array(hz * 3, 4096),
                sine_array(hz * 5, 4096)])

def play_for(sample_array, ms):
    "Play given samples, as a sound, for N ms."
    sound = pygame.sndarray.make_sound(sample_array)
    sound.play(-1)
    pygame.time.delay(ms)
    sound.stop()

def main():
    pygame.mixer.pre_init(sample_rate, -16, 1) # 44.1kHz, 16-bit signed, mono
    pygame.init()
    # play_for(sine_array(440, 4096), 500)
    play_for(second_harmonic(440), 500)
    # play_for(brass(440), 500)

if __name__ == '__main__':
    main()
