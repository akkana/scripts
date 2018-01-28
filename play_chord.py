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
import sys, os
import termios, fcntl   # For non-blocking key reads

sample_rate = 44100
sampling = 4096    # or 16384

# Notes = { "Ab" : 415.3, "A" : 440.0, "A#" : 466.16,
#           "Bb" : 466.16, "B" : 493.88,
#                          "C" : 523.25, "C#" : 554.37,
#           "Db" : 554.37, "D" : 587.33, "D#" : 622.25,
#           "Eb" : 622.25, "E" : 659.25,
#                          "F" : 698.46, "F#" : 739.99,
#           "Gb" : 739.99, "G" : 783.99, "G#" : 830.61
#         }

Notes = {
    "A"  : 220.000000,
    "A#" : 233.080000,
    "Ab" : 207.650000,
    "B"  : 246.940000,
    "Bb" : 233.080000,
    "C"  : 261.625000,
    "C#" : 277.185000,
    "D"  : 293.665000,
    "D#" : 311.125000,
    "Db" : 277.185000,
    "E"  : 329.625000,
    "Eb" : 311.125000,
    "F"  : 349.230000,
    "F#" : 369.995000,
    "G"  : 391.995000,
    "G#" : 415.305000,
    "Gb" : 369.995000,
}

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
    # In pygame 1.9.1, we can pass sample_wave directly,
    # but in 1.9.2 they changed the mixer to only accept ints.
    sound = pygame.sndarray.make_sound(sample_wave.astype(int))
    sound.play(-1)
    pygame.time.delay(ms)
    sound.stop()

def play_some_chords():
    length = 500
    wait = 1000

    print("Sine")
    play_for(sine_wave(440, 4096), length)
    pygame.time.delay(wait)

    print("Square")
    play_for(square_wave(440, 4096), length)
    pygame.time.delay(wait)
    print("Higher Square")
    play_for(square_wave(880, 4096), length)

    pygame.time.delay(wait)
    print("Triangle")
    play_for(sawtooth_wave(440, 4096, .5), length)  # triangle wave
    pygame.time.delay(wait)
    print("Sawtooth")
    play_for(sawtooth_wave(440, 4096, 1.), length)   # sawtooth wave

    pygame.time.delay(wait)
    print("Fundamental (sine)")
    play_for(fundamental(440), length)
    pygame.time.delay(wait)
    print("Third")
    play_for(third(440), length)
    pygame.time.delay(wait)
    print("Third, square")
    play_for(third(440, square_wave), length)
    pygame.time.delay(wait)
    print("Third, sawtooth")
    play_for(third(440, sawtooth_wave), length)
    pygame.time.delay(wait)
    print("Fifth")
    play_for(fifth(440), length)

    # Triads mostly don't work with sawtooth waves.
    # Maybe it's something to do with the number of samples
    # making some of the overtones cancel out.

    pygame.time.delay(wait)
    print("Major triad")
    play_for(major_triad(440), length)
    pygame.time.delay(wait)
    print("Major triad, square")
    play_for(major_triad(440, square_wave), length)
    pygame.time.delay(wait)
    print("Major triad, sawtooth")
    play_for(major_triad(440, sawtooth_wave), length)
    pygame.time.delay(wait)
    print("Minor triad")
    play_for(minor_triad(440), length)
    pygame.time.delay(wait)
    print("Minor with square wave")
    play_for(minor_triad(440, square_wave), length)

    pygame.time.delay(wait)
    print("Diminished")
    play_for(diminished(440), length)

    pygame.time.delay(wait)
    print("Seventh")
    play_for(seventh(440), length)
    pygame.time.delay(wait)
    print("Minor seventh")
    play_for(minor_seventh(440), length)

    pygame.time.delay(wait)
    print("Minor seventh, square")
    play_for(minor_seventh(440, square_wave), length)
    pygame.time.delay(wait)
    print("Minor seventh, sawtooth")
    play_for(minor_seventh(440, sawtooth_wave), length)

    pygame.time.delay(wait)
    print("Major seventh")
    play_for(major_seventh(440), length)
    pygame.time.delay(wait)
    print("Major seventh, square")
    play_for(major_seventh(440, square_wave), length)
    pygame.time.delay(wait)
    print("Major seventh, sawtooth")
    play_for(major_seventh(440, sawtooth_wave), length)

def parse_chord(ns, default_duration=300):
    '''Parse a single chord notation, like E4,G4:2.
       Returns a list of frequencies (possibly empty) and a duration in ms.
    '''
    if ':' in ns:
        ns, durationstr = ns.strip().split(':')
        # everything after the colon is a duration
        duration = float(durationstr.strip())
    else:
        duration = 1.
    duration = int(duration * default_duration)

    freqlist = []
    indnotes = ns.strip().split(',')
    chord = None
    for ns in indnotes:
        if ns[0] in Notes:
            if len(ns) > 1 and (ns[1] == 'b' or ns[1] == '#'):
                # It's a sharp or flat
                freqlist.append(Notes[ns[:2]])
                ns = ns[2:]
            else:
                # No sharp or flat
                freqlist.append(Notes[ns[0]])
                ns = ns[1:]
            try:
                octave = float(ns)    # which octave is it?
                freqlist[-1] *= 2 ** (octave-1)
                ns = ns[1:]
            except:
                pass
    return freqlist, duration

def play_notes(notestring, waveform=None):
    '''notestring is a string with a format like this:
    D4,F4 E4,G4:2 Bb3   note#octave,note#octave:duration
    where either octave or duration can be omitted to use the default (1).
    Duration can be a decimal.
    # or b can follow a note letter.
    Omit the note to indicate a rest, e.g. :1.
    '''
    if not waveform:
        waveform = square_wave

    for ns in notestring.split():
        freqlist, duration = parse_chord(ns)
        if freqlist:
            chord = waveform(freqlist[0], sampling)
            for freq in freqlist[1:]:
                chord = sum([chord, waveform(freq, sampling)])
            play_for(chord, duration)
        else:
            # If we didn't get any frequencies, then rest.
            pygame.time.delay(duration)
        pygame.time.delay(80)

def play_from_keyboard():
    from keyreader import KeyReader
    keyreader = KeyReader(echo=False, block=True)
    keyboard_keys = {
        # Middle row: black keys
        'a': 'Ab', 's': 'A#',         'f': 'C#', 'g': 'D#',
        'j': 'F#', 'k': 'G#', 'l': 'A#2', '\'': 'C2#',
        # Bottom row:
        'z': 'A', 'x': 'B', 'c': 'C', 'v': 'D',
        'b': 'E', 'n': 'F', 'm': 'G',
        ',': 'A2', '.': 'B2', '/': 'C2'
                    }
    while True:
        key = keyreader.getch()
        if key == 'q':
            keyreader = None
            return
        if key in keyboard_keys:
            freqlist, duration = parse_chord(keyboard_keys[key], 200)
            note = square_wave(freqlist[0], sampling)
            play_for(note, duration)

def init():
    pygame.mixer.pre_init(sample_rate, -16, 1) # 44.1kHz, 16-bit signed, mono
    pygame.init()

def main():
    init()

    if len(sys.argv) <= 1:
        return play_some_chords()

    if sys.argv[1].lower() == "-h" or sys.argv[1].lower() == "--help":
        print("Usage: %s [scale|imperial|cmajor|other note string]") % os.path.basename(sys.argv[0])
        return

    if sys.argv[1].lower() == "scale":
        # Play a scale
        return play_notes("C D E F G A2 B2 C2")

    if sys.argv[1].lower() == "imperial" or sys.argv[1].lower() == "empire":
        # Play the first line of the Imperial March
        return play_notes("G G G Eb:.75 Bb2:.25 G Eb:.75 Bb2:.25 G")

    if sys.argv[1].lower() == "cmajor":
        # Play a simple C-major triad
        return play_notes("C,E,G")

    if sys.argv[1].lower() == "chopsticks":
        return play_notes("F,G:.5 F,G:.5 F,G:.5 F,G:.5 F,G:.5 F,G:.5 E,G:.5 E,G:.5 E,G:.5 E,G:.5 E,G:.5 E,G:.5 D,B2:.5 D,B2:.5 D,B2:.5 D,B2:.5 D,A2:.5 D,B2:.5 C,C2:1.2")

    if sys.argv[1] == "keyboard":
        return play_from_keyboard()

    for s in sys.argv[1:]:
        play_notes(s)

if __name__ == '__main__':
    main()
