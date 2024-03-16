#!/usr/bin/env python3

"""A program to help with practicing guitar.
   Can run a metronome, play notes, display guitar tablature for notes,
   etc.
   Eventually will include flashcard-style quizzes.
"""

# The sox manual gives the example:
# play -n synth pl G2 pl B2 pl D3 pl G3 pl D4 pl G4 \
#      delay 0 .05 .1 .15 .2 .25 remix - fade 0 4 .1 norm -1
# pl is apparently short for pluck
# Add vol 0.25 *at the end* to reduce volume.
# fade is timed from the beginning, so make sure it's long enough
# to cover all the notes plus your desired fade time,
# or else you'll miss the later notes.
# Single plucked string: play -n synth 0 pluck E3
# Here's a metronome:
#  play -n -c1 synth 0.004 sine 2000 \
#       pad $(awk "BEGIN { print 60/$bpm -.004 }") repeat $beats vol $volume



"""Other interesting URLs re Python and guitar:
https://www.mvanga.com/blog/deriving-guitar-theory-in-400-lines-of-python
https://alvaroaguirre.com/blog/chord_of_the_day.html
https://briancaffey.github.io/2018/04/26/generating-music-from-guitar-tabs-with-python.html/

The last answer in this thead might explain why pygame.midi never makes a sound:
https://forums.raspberrypi.com/viewtopic.php?t=116715

Good breakdown of the sox/play commandline arguments:
https://scruss.com/blog/2017/12/19/synthesizing-simple-chords-with-sox/
Breakdown:
play -n               use no input file
     synth            synthesize notes
     pl G2            first note is a G2 with a waveform like a plucked string
     ....
     delay 0 .05 .1 .15 .2 .25    delay the first note 0, second .05, etc.
     remix            mix the tones in an internal pipe to the output
     fade 0 1 .095    fade the audio smoothly down to nothing in 1 s
     norm -1          normalize the volume to -1 dB.
You can also save them: right after the -n, add
     -r 16000 -b 16 "chord-${chord}.wav"
"""

# https://www.101computing.net/guitar-chords-reader/

import time
import os
import subprocess


#A Python Dictionary matching chord names with "fret notation"
GUITAR_CHORDS = {
    "D": "xx0232",
    "A":"x02220",
    "E": "022100",
    "G": "320033",
    "C": "x32010",
    "F": "x3321x",
    "Am": "x02210",
    "Dm": "xx0231",
    "Em": "022000"
}

# Notes must start with C: in sox, A2 is higher than C2
# so a scale goes C2, D2 ... G2, A2, B2, C2, D3 ...
# Use sharps rather than flats for the notes.
basicnotes = [ "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B" ]
ALLNOTES = [ note + '2' for note in basicnotes ] + \
           [ note + '3' for note in basicnotes ] + \
           [ note + '4' for note in basicnotes ]

GUITAR_STRINGS = [ "E2", "A2", "D3", "G3", "B3", "E4" ]

DELAY_BETWEEN_STRINGS = .06


def fretboard_to_note(stringbase, fret):
    stringnote = ALLNOTES.index(stringbase)
    print("string", stringbase, "fret", fret, "->", ALLNOTES[stringnote + fret])
    return ALLNOTES[stringnote + fret]


def chord_to_notes(chord_tab):
    """Take notation like "xx0232" and turn it into a list of notes like E2
    """
    chord_notes = []
    for stringno, string_fret in enumerate(chord_tab):
        if string_fret == 'x' or string_fret == ' ':
            continue
        chord_notes.append(fretboard_to_note(GUITAR_STRINGS[stringno],
                                             int(string_fret)))
    return chord_notes


#A procedure to display where to position your fingers to play a given chord
def display_chord(chord):
    fretNotation = GUITAR_CHORDS[chord]

    print("  " + chord)
    nut=""
    for string in fretNotation:
        if string=="x":
            nut = nut + " x"  # x means don't play this string
        else:
            nut = nut + " _"
    print(nut)

    for fretNumber in range(1,5):
        fret=""
        for string in fretNotation:
            if string==str(fretNumber):
                fret = fret + " O"
            else:
                fret = fret + " |"
        print(fret)


def play_chord(chordname, volume=.25):
    args = [ "play", "-n", "synth" ]
    # pl G2 pl B2 pl D3 pl G3 pl D4 pl G4 \
    #      delay 0 .05 .1 .15 .2 .25 remix - fade 0 4 .1 norm -1
    chordnotes = chord_to_notes(GUITAR_CHORDS[chordname])
    for note in chordnotes:
        args.append("pl")
        args.append(note)
    args.append("delay")
    delay = 0
    for ch in chordnotes:
        args.append(str(delay))
        delay += DELAY_BETWEEN_STRINGS
    args += [ "remix", "-",
              "fade", "0", str(delay + 1.5), ".1",
              "norm", "-1", "vol", str(volume) ]
    print(' '.join(args))
    subprocess.call(args)


def play_notes(notestr, delay=.6):
    """Play a sequence of notes, comma separated, e.g. "C1,C2,C3"
       with a single sox play command.
       Useful for testing.
    """
    notes = notestr.split(',')
    args = [ "play", "-n", "synth" ]
    for note in notes:
        args.append("pl")
        args.append(note)
    args.append("delay")
    d = 0
    for note in notes:
        args.append(str(d))
        d += delay
    args += [ "remix", "-",
              "fade", "0", str(len(notes) * delay + 2), ".1",
              "norm", "-1", "vol", ".2" ]
    print(' '.join(args))
    subprocess.call(args)


song = "C,D,G,Em,C,D,G,Em"

# read song, one chord at a time
song_chords = song.split(",")
for chord in song_chords:
    display_chord(chord)
    play_chord(chord)
    # time.sleep(.75)


