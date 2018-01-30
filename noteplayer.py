#!/usr/bin/python

"""Demonstrate harmonic synthesis in Python using NumPy.

Call init() first."""

from __future__ import print_function

# Originally from:
#     http://osdir.com/ml/culture.people.kragen.hacks/2007-11/msg00000.html
# and https://mail.python.org/pipermail/tutor/2009-January/066173.html

# Unrelated, but also check out:
# play -n synth pl G2 pl B2 pl D3 pl G3 pl D4 pl G4 \
#                delay 0 .05 .1 .15 .2 .25 remix - fade 0 4 .1 norm -1
# you can use # and b for sharps/flats, e.g. G#4 is a high G sharp.
# Check the SoX(1) man page for more fun examples.

import pygame, pygame.sndarray
import time
import numpy
import scipy.signal
import sys, os
import termios, fcntl   # For non-blocking key reads
from threading import Timer

sample_rate = 44100
sampling = 4096    # or 16384

# One octave. Other octaves can be calculated.
A  = 220.000000
Ab = 207.650000
B  = 246.940000
Bb = 233.080000
C = 261.625000
D = 293.665000
Db = 277.185000
E = 329.625000
Eb = 311.125000
F = 349.230000
G = 391.995000
Gb = 369.995000

sound_playing = None

# We need to keep a list of waves playing, so we can add or subtract them.
# But numpy arrays can't be removed from lists, because of weirdness in
# their comparison operator. So instead, use a dictionary where each
# wave has a key corresponding to its frequency.
waves_playing = {}

#
# Some waveforms. These functions can be passed in to note-playing functions.
#

def sine_wave(hz, peak=sampling, n_samples=sample_rate):
    """Compute N samples of a sine wave with given frequency and peak amplitude.
       Defaults to one second.
    """
    length = sample_rate / float(hz)
    omega = numpy.pi * 2 / length
    xvalues = numpy.arange(int(length)) * omega
    onecycle = peak * numpy.sin(xvalues)
    return numpy.resize(onecycle, (n_samples,)).astype(numpy.int16)

def square_wave(hz, peak=sampling, duty_cycle=.5, n_samples=sample_rate):
    """Compute N samples of a sine wave with given frequency and peak amplitude.
       Defaults to one second.
    """
    t = numpy.linspace(0, 1, 500 * 440/hz, endpoint=False)
    wave = scipy.signal.square(2 * numpy.pi * 5 * t, duty=duty_cycle)
    wave = numpy.resize(wave, (n_samples,))
    # Square waves sound much louder than sine, so divide peak by 2.
    return (peak / 2 * wave.astype(numpy.int16))

def sawtooth_wave(hz, peak=sampling,
                  rising_ramp_width=1, n_samples=sample_rate):
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

#
# Basic note-playing.
#

def play_current_waves():
    global sound_playing

    if not waves_playing:
        # print("No current waves to play")
        silence()
        return

    chord =  numpy.zeros(sample_rate)
    for w in waves_playing:
        chord = sum([chord, waves_playing[w]])

    # Turn that into a sound and play it:
    sound = pygame.sndarray.make_sound(chord.astype(int))
    sound.play(-1)
    if sound_playing:
        sound_playing.stop()
    sound_playing = sound

def start_note(freqlist, waveform=square_wave, additive=True):
    '''Start a note of a given frequency and waveform.
       freqlist can be either a list or a single frequency (float).
       If additive, we'll add it to whatever's already playing;
       otherwise it will replace the current sound.
    '''
    global waves_playing

    if not freqlist:
        return

    if not additive:
        waves_playing = {}

    if hasattr(freqlist, "__getitem__"):
        wave =  numpy.zeros(sample_rate)
        key = freqlist[0]
        for freq in freqlist:
            wave = sum(wave, waveform(freq))
            waves_playing[freq] = wave
    else:
        wave = waveform(freqlist)
        key = freqlist

    waves_playing[key] = wave

    # Play it along with whatever we already had.
    # Don't actually do this: better to make all the changes first,
    # then have the caller call play_current_waves()
    # play_current_waves()
    return key

def stop_note(wav):
    '''Subtract waves_playing[wav] from what we're currently playing.
    '''
    global waves_playing

    try:
        del waves_playing[wav]
    except:
        # print("Couldn't delete", wav, "from waves_playing:")
        # print(waves_playing)
        pass

def silence():
    global sound_playing, waves_playing

    if sound_playing:
        sound_playing.stop()
    waves_playing = {}
    sound_playing = None

def init():
    pygame.mixer.pre_init(sample_rate, -16, 1) # 44.1kHz, 16-bit signed, mono
    pygame.init()

def stop():
    if sound_playing:
        stop_note(sound_playing)
    pygame.mixer.stop()

def main():
    init()

    c = start_note(C)
    time.sleep(1)
    e = start_note(E)
    time.sleep(1)
    stop_note(c)
    time.sleep(1)
    stop_note(e)

    stop()

if __name__ == '__main__':
    main()
