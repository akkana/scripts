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

def make_chord(hz, ratios):
    """Make a chord based on a list of frequency ratios."""
    sampling = 4096    # or 16384
    chord = sine_array(hz, sampling)
    for r in ratios[1:]:
        chord = sum([chord, sine_array(hz * r / ratios[0], sampling)])
    return chord

# Some popular chords and their frequency ratios:
def fundamental(hz):
    return make_chord(hz, [1])

def third(hz):
    return make_chord(hz, [4, 5])

def fifth(hz):
    return make_chord(hz, [2, 3])

def major(hz):
    return make_chord(hz, [4, 5, 6])

def minor(hz):
    return make_chord(hz, [10, 12, 15])

def diminished(hz):
    return make_chord(hz, [160, 192, 231])

def seventh(hz):
    return make_chord(hz, [20, 25, 30, 36])

def minor_seventh(hz):
    return make_chord(hz, [10, 12, 15, 18])

def major_seventh(hz):
    return make_chord(hz, [8, 10, 12, 15])

def brass(hz):
    "Compute a sound with some odd harmonics. Doesn't really sound brassy."
    return sum([sine_array(hz, 4096),
                sine_array(hz * 3, 4096),
                sine_array(hz * 5, 4096)])

# https://mail.python.org/pipermail/tutor/2009-January/066173.html
def waves(*chord):
    # Compute the harmonic series for a vector of frequencies
    # Create square-like waves by adding odd-numbered overtones for each
    # fundamental tone in the chord.
    # The amplitudes of the overtones are inverse to their frequencies.
    h=9
    ot=3
    harmonic=sine_array(chord[0],4096)
    while (ot<h):
        if (ot*chord[0])<(sample_rate/2):
	    harmonic=harmonic+(sine_array(chord[0]*ot, 4096/(2*ot)))
        else:
	    harmonic=harmonic+0
            ot+=2
    for i in range(1,len(chord)):
        harmonic+=(sine_array(chord[i], 4096))

        if (ot*chord[i])<(sample_rate/2):
            harmonic=harmonic+(sine_array(chord[i]*ot, 4096/(2*ot)))
        else:
            harmonic=harmonic+0
        ot+=2
    return harmonic

def play_for(sample_array, ms):
    "Play given samples, as a sound, for N ms."
    sound = pygame.sndarray.make_sound(sample_array)
    sound.play(-1)
    pygame.time.delay(ms)
    sound.stop()

def main():
    length = 1000
    pygame.mixer.pre_init(sample_rate, -16, 1) # 44.1kHz, 16-bit signed, mono
    pygame.init()

    # play_for(sine_array(440, 4096), length)
    # play_for(second_harmonic(440), length)
    # play_for(sine_array(440, 4096) + sine_array(440 * 5/4, 4096), length)
    play_for(brass(440), length)

    play_for(fundamental(440), length)
    play_for(third(440), length)
    play_for(fifth(440), length)

    play_for(major(440), length)
    play_for(minor(440), length)
    play_for(diminished(440), length)
    play_for(seventh(440), length)
    play_for(minor_seventh(440), length)
    play_for(major_seventh(440), length)

    pygame.time.delay(300)

    play_for(waves(440,550,660,770,880), length)

if __name__ == '__main__':
    main()
