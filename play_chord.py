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
import time, random
import numpy
import scipy.signal
import sys

sample_rate = 44100

def sine_wave(hz, peak, n_samples=sample_rate):
    """Compute N samples of a sine wave with given frequency and peak amplitude.
       Defaults to one second.
    """
    length = sample_rate / float(hz)
    omega = numpy.pi * 2 / length
    xvalues = numpy.arange(int(length)) * omega
    onecycle = peak * numpy.sin(xvalues)
    return numpy.resize(onecycle, (n_samples,)).astype(numpy.int16)

def square_wave(hz, peak, duty_cycle=.5, n_samples=sample_rate):
    """Compute N samples of a sine wave with given frequency and peak amplitude.
       Defaults to one second.
    """
    t = numpy.linspace(0, 1, 500 * 440/hz, endpoint=False)
    wave = scipy.signal.square(2 * numpy.pi * 5 * t, duty=duty_cycle)
    wave = numpy.resize(wave, (n_samples,))
    # Square waves sound much louder than sine, so divide peak by 2.
    return (peak / 2 * wave.astype(numpy.int16))

def sawtooth_wave(hz, peak, rising_ramp_width=1, n_samples=sample_rate):
    """Compute N samples of a sine wave with given frequency and peak amplitude.
       Defaults to one second.
       rising_ramp_width is the percentage of the ramp spend rising:
       .5 is a triangle wave with equal rising and falling times.
    """
    t = numpy.linspace(0, 1, 500 * 440/hz, endpoint=False)
    wave = scipy.signal.sawtooth(2 * numpy.pi * 5 * t, width=rising_ramp_width)
    wave = numpy.resize(wave, (n_samples,))
    # Sawtooth waves sound very quiet, so multiply peak by 4.
    return (peak * 4 * wave.astype(numpy.int16))

def make_chord(hz, ratios, waveform=None):
    """Make a chord based on a list of frequency ratios.
       using a given waveform (defaults to a sine wave).
    """
    sampling = 4096    # or 16384
    if not waveform:
        waveform = sine_wave
    chord = waveform(hz, sampling)
    for r in ratios[1:]:
        chord = sum([chord, waveform(hz * r / ratios[0], sampling)])
    return chord

# Some popular chords and their frequency ratios:
def fundamental(hz, waveform=None):
    return make_chord(hz, [1])

def third(hz, waveform=None):
    return make_chord(hz, [4, 5], waveform)

def fifth(hz, waveform=None):
    return make_chord(hz, [2, 3], waveform)

def major_triad(hz, waveform=None):
    return make_chord(hz, [4, 5, 6], waveform)

def minor_triad(hz, waveform=None):
    return make_chord(hz, [10, 12, 15], waveform)

def diminished(hz, waveform=None):
    return make_chord(hz, [160, 192, 231], waveform)

def seventh(hz, waveform=None):
    return make_chord(hz, [20, 25, 30, 36], waveform)

def minor_seventh(hz, waveform=None):
    return make_chord(hz, [10, 12, 15, 18], waveform)

def major_seventh(hz, waveform=None):
    return make_chord(hz, [8, 10, 12, 15], waveform)

def play_for(sample_wave, ms):
    """Play given samples, as a sound, for ms milliseconds."""
    sound = pygame.sndarray.make_sound(sample_wave)
    sound.play(-1)
    pygame.time.delay(ms)
    sound.stop()

def main():
    length = 500
    wait = 1000
    pygame.mixer.pre_init(sample_rate, -16, 1) # 44.1kHz, 16-bit signed, mono
    pygame.init()

    print "Sine"
    play_for(sine_wave(440, 4096), length)
    pygame.time.delay(wait)

    print "Square"
    play_for(square_wave(440, 4096), length)
    pygame.time.delay(wait)
    print "Higher Square"
    play_for(square_wave(880, 4096), length)

    pygame.time.delay(wait)
    print "Triangle"
    play_for(sawtooth_wave(440, 4096, .5), length)  # triangle wave
    pygame.time.delay(wait)
    print "Sawtooth"
    play_for(sawtooth_wave(440, 4096, 1.), length)   # sawtooth wave

    pygame.time.delay(wait)
    print "Fundamental (sine)"
    play_for(fundamental(440), length)
    pygame.time.delay(wait)
    print "Third"
    play_for(third(440), length)
    pygame.time.delay(wait)
    print "Third, square"
    play_for(third(440, square_wave), length)
    pygame.time.delay(wait)
    print "Third, sawtooth"
    play_for(third(440, sawtooth_wave), length)
    pygame.time.delay(wait)
    print "Fifth"
    play_for(fifth(440), length)

    # Triads mostly don't work with sawtooth waves.
    # Maybe it's something to do with the number of samples
    # making some of the overtones cancel out.

    pygame.time.delay(wait)
    print "Major triad"
    play_for(major_triad(440), length)
    pygame.time.delay(wait)
    print "Major triad, square"
    play_for(major_triad(440, square_wave), length)
    pygame.time.delay(wait)
    print "Major triad, sawtooth"
    play_for(major_triad(440, sawtooth_wave), length)
    pygame.time.delay(wait)
    print "Minor triad"
    play_for(minor_triad(440), length)
    pygame.time.delay(wait)
    print "Minor with square wave"
    play_for(minor_triad(440, square_wave), length)

    pygame.time.delay(wait)
    print "Diminished"
    play_for(diminished(440), length)

    pygame.time.delay(wait)
    print "Seventh"
    play_for(seventh(440), length)
    pygame.time.delay(wait)
    print "Minor seventh"
    play_for(minor_seventh(440), length)

    pygame.time.delay(wait)
    print "Minor seventh, square"
    play_for(minor_seventh(440, square_wave), length)
    pygame.time.delay(wait)
    print "Minor seventh, sawtooth"
    play_for(minor_seventh(440, sawtooth_wave), length)

    pygame.time.delay(wait)
    print "Major seventh"
    play_for(major_seventh(440), length)
    pygame.time.delay(wait)
    print "Major seventh, square"
    play_for(major_seventh(440, square_wave), length)
    pygame.time.delay(wait)
    print "Major seventh, sawtooth"
    play_for(major_seventh(440, sawtooth_wave), length)

if __name__ == '__main__':
    main()
