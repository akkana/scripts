#!/usr/bin/env python3

"""A program to help with practicing guitar.
   Can run a metronome, play notes, display guitar tablature for notes,
   and give a flashcard-style quiz.
   Copyright 2024 by Akkana: share and enjoy under the GPLv2 or later.
"""

# Uses chord display code and fret notation adapted from
# https://www.101computing.net/guitar-chords-reader/

import subprocess
import random
import argparse
import time
import xdg.BaseDirectory
import os, sys

try:
    import pyfiglet
except:
    print("pyfiglet isn't available: can't draw big chord names")


# If there's no GUITARFLASH env variable or ~/.config/guitarflash.conf,
# show only these chords (space separated):
BEGINNER_CHORDS = "D A E"


# A Python Dictionary matching chord names with "fret notation"
GUITAR_CHORDS = {
    "D": "xx0232",
    "A": "x02220",
    "E": "022100",
    "G": "320003",
    "C": "x32010",
    "F": "x3321x",
    "Am": "x02210",
    "Dm": "xx0231",
    "Em": "022000",
    "G2": "320033",
    "B": "x24442",
    "F#m": "244222",
    "B7": "o212o2",
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

Volume = 1

Metroproc = None


def fretboard_to_note(stringbase, fret):
    stringnote = ALLNOTES.index(stringbase)
    # print("string", stringbase, "fret", fret,
    #       "->", ALLNOTES[stringnote + fret])
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
    """Play a chord, specified by name like "Em".
    """
    args = [ "play", "-nq", "-t", "alsa", "synth" ]
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
    # print(' '.join(args))
    subprocess.call(args)


def play_notes(notestr, delay=.6):
    """Play a sequence of notes, comma separated, e.g. "C1,C2,C3"
       with a single sox play command.
       Useful for testing.
    """
    notes = notestr.split(',')
    args = [ "play", "-nq", "-t", "alsa", "synth" ]
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
    # print(' '.join(args))
    subprocess.call(args)


def start_metronome(bpm, duration=None):
    global Metroproc
    args = [ "play", "-nq", "-t", "alsa",
             "-c1", "synth", "0.004", "sine", "2000",
             "pad", str(60/bpm -.004),
             "repeat", str(bpm * duration) if duration else '-',
             "vol", str(Volume) ]
    print(args)
    Metroproc = subprocess.Popen(args, close_fds=True)


def stop_metronome():
    global Metroproc
    if not Metroproc:
        # print("Metronome isn't running")
        return
    print("Stopping metronome")
    Metroproc.kill()
    Metroproc = None


def sanity_check(chords):
    """Do all the indicated chords actually exist?"""
    goodchords = []
    badchords = set()
    for c in chords:
        if c in GUITAR_CHORDS:
            goodchords.append(c)
        else:
            badchords.add(c)

    if badchords:
        print("Ignoring unsupported chords", ' '.join(badchords))

    if not goodchords:
        print("No chords left; defaulting to beginner chords")
        return BEGINNER_CHORDS,

    return goodchords


def chord_flashcards(chords=BEGINNER_CHORDS, metronome=None):
    chords = sanity_check(chords)
    if metronome:
        start_metronome(metronome)
    lastchord = None
    try:
        while True:
            print("\n\n\n")
            chord = random.choice(chords)
            if chord == lastchord:
                continue
            lastchord = chord
            try:
                print(pyfiglet.figlet_format(chord))
            except:
                print(f"\n{ chord }\n")

            time.sleep(2)
            for i in range(2):
                play_chord(chord)
            time.sleep(1)

            display_chord(chord)
            for i in range(2):
                play_chord(chord)

    except KeyboardInterrupt:
        print("Exiting")

    stop_metronome()


def read_config():
    """Look for GUITARFLASH env variable or ~/.config/guitarflash/*.conf
       for a list of chords to show.
       Return a list of chord name strings, defaulting to BEGINNER_CHORDS.
       Chords are not unique; if a chord name repeats, it will be shown more.
       Suggested conf file name is $XDG_CONFIG_HOME/guitarflash/guitarflash.conf
       but you can have multiple files; everything matching
       $XDG_CONFIG_HOME/guitarflash/*.conf will be read.
    """
    if "GUITARFLASH" in os.environ:
        return os.environ["GUITARFLASH"].split()

    try:
        chords = []
        confdir = os.path.join(xdg.BaseDirectory.xdg_config_home,
                               "guitarflash")
        for conffile in os.listdir(confdir):
            if not conffile.endswith(".conf"):
                continue
            with open(os.path.join(confdir, conffile)) as fp:
                for line in fp:
                    chords += line.split()
        if chords:
            return chords
        print("Didn't find any chords in", confdir)
    except Exception as e:
        print("Exception finding conffiles; showing beginner chords")
        print(e)
        pass

    return BEGINNER_CHORDS


if __name__ == '__main__':
    # test_main()

    parser = argparse.ArgumentParser(description="Guitar Flashcards")
    parser.add_argument('-c', "--chords", default=None, action="store",
                        help="chords to use (you can also specify them in "
                        "GUITARFLASH env variable or "
                        "XDG_CONFIG_HOME/guitarflash/*.conf")
    parser.add_argument('-m', "--bpm", "--metronome",
                        action="store", default=0, dest="bpm", type=int,
                        help='Metronome Beats per Minute')
    parser.add_argument('-v', "--volume",
                        action="store", default=1, dest="volume", type=float,
                        help='Metronome Beats per Minute')
    args = parser.parse_args(sys.argv[1:])
    Volume = args.volume

    # Get a list of chords to use, otherwise, show just beginner chords
    if args.chords:
        chords = args.chords.split()
    else:
        chords = read_config()

    chord_flashcards(chords=chords, metronome=args.bpm)
