#!/usr/bin/env python3

"""A program to help with practicing guitar.
   Can run a metronome, play notes, display guitar tablature for notes,
   and give several types of flashcard-style quiz.
   Copyright 2024 by Akkana: share and enjoy under the GPLv2 or later.
"""

# Uses sox play to play the notes/chords, so this script will probably
# only work on Linux.

# Uses chord display code and fret notation adapted from
# https://www.101computing.net/guitar-chords-reader/

import subprocess
import random
import re
import argparse
import time
import xdg.BaseDirectory
import os, sys

try:
    import pyfiglet
except:
    print("pyfiglet isn't available: can't draw big chord names")


# How many times to repeat each note or chord that's played
REPEAT_PLAY = 2


# A Python Dictionary matching chord names with "fret notation"
GUITAR_CHORDS = {
    "D": "xx0232",
    "A": "x02220",
    "E": "022100",
    "G": [ "320003", "320033"],
    "C": "x32010",
    "Am": "x02210",
    "Dm": "xx0231",
    "Em": "022000",

    "B": "x24442",
    "F": "133211",
    "miniF": "xx3211",
    "F#m": "244222",

    # "stuck 3-4 chords:
    "bigG": "32oo22",
    "rockG": "3xoo33",
    "Cadd9": [ "x32o33", "x32o3o" ],
    # A7sus4 and Dsus4 are in here too
    "Emin7": "022033",
    "Dadd11": "2xo233",
    "F69": "xx3233",

    # "sus" chords
    "Dsus2": "xx0230",
    "Dsus4": "xx0233",
    "Asus2": "x02200",
    "Asus4": "x02230",
    "A7sus4": "xo2233",
    "Esus2": "024400",
    "Esus4": "022200",

    # barre chords
    "F": "x3321x",
    "Bm": "x24432",
    "Bsus2": "x24422",

    # 7s
    "Fmaj7": [ "xx3210", "x33210" ],
    "B7": "x21202",
    "D7": "'xx0212",
    "Dmaj7": "xx0222",
    "G7": "320001",
    "B7": [ "020100", "022130", "021202" ],
    "E7": "020100",
    "A7": [ "x02020", "x02223" ],
    "C7": "x32310",

    # 6
    "F6": "13o2xx",

    # "Slash" chords
    "G/B": [ "x20033", "x20003" ],
    "G6/B": "x20030",
    "D/F#": [ "200232", "2x023x" ],
    "G/F#": "2x0033",
    "C/G": [ "332010", "3x2010" ],
    "C/E": [ "032010", "xx2010" ],
    "C/B": "x22010",
    "Cadd2/B": "x20010",
    "A/E": "0x2220",
    "D/A": "x00232",
    "F/A": "x03211",
    "F/G": "3x321x",   # Can move this one up and down the neck
    "A11/E": "000000",

    #  Harder slash chords
    # "A/C#": "x4222x",
    # "Am7/G": "3x2010",
    # "G/F": "1x0033",
    # "Am/F#": "2x2210",
}


# Chord groups that might need to be practiced at various levels
CHORD_GROUPS = {
    "beginner1": [ "D", "A", "E", "G" ],
    "beginner": [ "D", "A", "E", "G", "C", "Am", "Dm" ],
    "stuck34": [ "bigG", "rockG", "Cadd9", "Dsus4", "A7sus4",
                 # "Emin7", "Dadd11", "F69"
               ],
    "sus": [ "Dsus2", "Dsus4", "Asus2", "Asus4", "A7sus4", "Esus2", "Esus4" ],
    "7": [ "G7", "B7", "E7", "A7", "C7",
           # "Fmaj7", "D7", "Dmaj7"
         ],
    "slash": [ "G/B", "G6/B", "D/F#", "G/F#", "C/G", "C/E", "C/B",
               "Cadd2/B", "A/E", "D/A", "F/A",
               # "A/C#", "Am7/G", "G/F", "Am/F#",
             ]
}


# Notes must start with C: in sox, A2 is higher than C2
# so a scale goes C2, D2 ... G2, A2, B2, C2, D3 ...
# Use sharps rather than flats for the notes.
basicnotes = [ "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B" ]
ALLNOTES = [ note + '2' for note in basicnotes ] + \
           [ note + '3' for note in basicnotes ] + \
           [ note + '4' for note in basicnotes ]

GUITAR_STRINGS = [ "E2", "A2", "D3", "G3", "B3", "E4" ]

#
# Build the individual note dictionary.
# Keys are note names ("A2"), values are (string, fret) pairs.
# The string number is 0 for low E2, 5 for high E4,
# NOT standard guitar string numbering that starts at the high string.
#
NOTE2STRING = {}    # will be filled by initialize()

# The 4th and 5th in various keys
PROGRESSIONS = {
    'c': [ 'f', 'g' ],
    'a': [ 'd', 'e' ],
    'e': [ 'a', 'b' ],
    'g': [ 'c', 'd' ],
}


# How slowly to "strum" a chord
DELAY_BETWEEN_STRINGS = .06

Volume = 1

Metroproc = None


def initialize():
    random.seed()

    for stringno, note in enumerate(GUITAR_STRINGS):
        fret = 0
        NOTE2STRING[note] = (stringno, 0)
        while True:
            note = up_one_semitone(note)
            fret += 1

            # We're done with this string if the new note equals the base
            # note (fret 0) on the next string,
            # OR if this is the last string and we've done enough frets.
            if stringno < len(GUITAR_STRINGS) - 1:
                if note == GUITAR_STRINGS[stringno+1]:
                    break

            else:    # last string
                if fret > 4:
                    break

            # If neither of those two conditions was satisfied,
            # stay on this string and add the note.
            NOTE2STRING[note] = (stringno, fret)


def up_one_semitone(note):
    """Given a note like "C2", return the designation
       for one semitone higher, "C#2"
    """
    noteletter = note[0]      # "C"
    noteoctave = note[-1]     # '2'

    # Is it already sharp?
    if note[1] == '#':
        if noteletter == 'G':
            return 'A' + noteoctave
        return chr(ord(noteletter) + 1) + noteoctave

    # Okay, not sharp.

    # Special case: B->C is where the octave number changes,
    # and B can't be sharpened, so return C of the next octave
    if noteletter == 'B':
        return 'C%d' % (int(noteoctave) + 1)

    # E is the other note that can't be sharpened.
    if noteletter == 'E':
        return 'F' + noteoctave

    # Sharpen the current note in the same octave
    return noteletter + "#" + noteoctave


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


def display_note(note):
    """Use NOTE2STRING to display notes as tablature
    """
    stringno, fret = NOTE2STRING[note]
    # print("string", stringno+1, "fret", fret)

    line = ''
    for stringNo in range(6):
        if stringno == stringNo and fret == 0:
            line += ' O'
        else:
            line += ' -'
    print(line)

    if fret > 5:
        maxfret = fret
    else:
        maxfret = 5
#
    for fretNo in range(1, maxfret):
        line = ""
        for stringNo in range(6):
            if stringno == stringNo and fret == fretNo:
                line += " #"
            else:
                line += " |"
        print(line)


def chord_to_string(chord):
    """Given a chord name like 'Am', return a string showing a tablature for it.
       Can also expand fret notation like 'xx0232'.
    """
    if len(chord) == 6:
        fretNotation = chord
    else:
        try:
            fretNotation = GUITAR_CHORDS[chord]
            # If there are multiple fingerings, display the first one
            if type(fretNotation) is list:
                fretNotation = fretNotation[0]
        except KeyError:
            print("Don't know the", chord, "chord", file=sys.stderr)
            return

    retstr = f"  {chord}\n"
    nut = ""
    for string in fretNotation:
        if string == "x":
            nut = nut + " x"  # x means don't play this string
        else:
            nut = nut + " _"
    retstr += "%s\n" % nut

    for fretNumber in range(1, 5):
        fret = ""
        for string in fretNotation:
            if string == str(fretNumber):
                # fret = fret + " O"
                # Various unicode blocks that could substitute.
                # None of them are particularly satisfying:
                # either they're too small, or they're big enough
                # but print as two characters wide.
                fret = fret + " \u2588"
                # fret = fret + " \u25A0"
                # fret = fret + " \u25CF"
            else:
                fret = fret + " |"
        retstr += '%s\n' % fret

    return retstr

def display_chord(chord):
    print(chord_to_string(chord))


CHORDS_PER_LINE = 5
INTERCHORD_SPACE = 4

def display_chords_compactly(chords):
    # print("Displaying chords:", chords)
    chordlines = []
    for i, chord in enumerate(chords):
        if i % CHORDS_PER_LINE == 0:
            if chordlines:
                print('\n'.join(chordlines))
            chordlines = []
        fretting = chord_to_string(chord)
        if not chordlines:
            chordlines = fretting.splitlines()
            continue

        # What's the longest chordline? Make a format string
        width = max([len(s) for s in chordlines]) + INTERCHORD_SPACE
        fmt = f'%-{width}s%s'

        # Put the new fretting to the right of the current chordline
        for i, line in enumerate(fretting.splitlines()):
             chordlines[i]= fmt % (chordlines[i], line)

    if chordlines:
        print('\n'.join(chordlines))


def play_chord(chordname):
    """Play a chord, specified by name like "Em".
    """
    args = [ "play", "-nq", "-t", "alsa", "synth" ]
    # pl G2 pl B2 pl D3 pl G3 pl D4 pl G4 \
    #      delay 0 .05 .1 .15 .2 .25 remix - fade 0 4 .1 norm -1
    if type(GUITAR_CHORDS[chordname]) is list:
        chordnotes = chord_to_notes(GUITAR_CHORDS[chordname][0])
    else:
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
              "norm", "-1", "vol", str(Volume) ]
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
              "norm", "-1", "vol", str(Volume) ]
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


def sanity_check_chords(chords):
    """Do all the indicated chords actually exist?
       Also expand shorthand like "beginner" or "7".
    """
    # print("Sanity checking chords:", chords)
    # goodchords is a list, not a set. That means you can specify a chord
    # multiple times if you want its flashcard to come up more often.
    goodchords = []
    badchords = set()
    for c in chords:
        if c in GUITAR_CHORDS:
            goodchords.append(c)
        elif c in CHORD_GROUPS:
            expandchords = sanity_check_chords(CHORD_GROUPS[c])
            for e in expandchords:
                goodchords.append(e)
        # Also accept specifiers like 020200
        elif len(c) == 6:
            goodchords.append(c)
        else:
            badchords.add(c)

    if badchords:
        print("Ignoring unsupported chords", ' '.join(badchords))

    return goodchords


def bigtext(s):
    if 'pyfiglet' in sys.modules:
        return pyfiglet.figlet_format(s)
    return "=== " + s


lastchord = None

def chord_flashcard(chords, metronome=None):
    """Run one chord flashcard"""

    global lastchord

    while True:
        chord = random.choice(chords)
        if chord == lastchord:
            continue
        lastchord = chord
        break

    print("\n\n\nchord:")
    print(bigtext(chord))

    time.sleep(2)
    for i in range(2):
        play_chord(chord)
    time.sleep(1)

    display_chord(chord)
    for i in range(REPEAT_PLAY):
        play_chord(chord)


def note_flashcard(allow_sharps=False, just_strings=False):
    """Run one note flashcard"""
    while True:
        note = random.choice(list(NOTE2STRING.keys()))
        if allow_sharps or '#' not in note:
            break

    print("\n\n\nnote:")
    print(bigtext(note))
    time.sleep(3)
    play_notes(note)
    time.sleep(3)
    display_note(note)
    time.sleep(1)
    for i in range(REPEAT_PLAY):
        play_notes(note)
        time.sleep(1)


def test_chord_progressions():
    keys = list(PROGRESSIONS.keys())
    print("Input the fourth and fifth for each key:")
    while True:
        key = random.choice(keys)
        print("%s: " % key, end='')
        sys.stdout.flush()
        chords = re.split(r'[\s,]+', input())
        chords = [ c.lower() for c in chords ]
        if chords == PROGRESSIONS[key]:
            print("Correct!")
        else:
            print("Sorry, no, it's %s" % ' '.join(PROGRESSIONS[key]))


def random_c_song(num_chords=None, delaysec=2, structure=None):
    """Play/print random chords chosen from the key of C:
       C Dm Em F G Am
       (Like the JustinGuitar "Dice Songwriting" lesson)
       Structure is a list of strings that functions
       like a rhyme scheme for chords.
       For example, [ "A", "A", "B", "A", "A", "B", "C", "B" ]
       will choose numchords chords (default 4) for the main part of the song
       and will play them twice; then a refrain of another numchords chords,
       then repeat that again, then a break, then the refrain again.
       Instead of single letters you can use words, like "verse,chorus"
       separated by commas or spaces.
       A string argument with no commas or spaces will be split
       into individual letters.
    """
    key_chords = [ "C", "Dm", "Em", "F", "G", "Am" ]

    if structure:
        if not num_chords:
            num_chords = 4
        if type(structure) is str:
            if ' ' in structure or ',' in structure:
                structure = re.split(r'[\s,]+', structure)
                print("split by commas/spaces:", structure)
            else:
                structure = list(structure)
                print("split into list", structure)
        songstruct = {}
        for part in structure:
            if part in songstruct:
                continue
            songstruct[part] = []
            for i in range(num_chords):
                songstruct[part].append(random.choice(key_chords))
        print("Song structure:")
        from pprint import pprint
        pprint(songstruct)
        print(structure)

        for part in structure:
            for chord in songstruct[part]:
                print(chord, end=' ')
                sys.stdout.flush()
                play_chord(chord)
        print()
        return

    # Otherwise, just play random chords.
    if not num_chords:
        num_chords = 16
    for i in range(num_chords):
        chord = random.choice(key_chords)
        print(f"{chord} ", end='')
        sys.stdout.flush()
        play_chord(chord)
    print()


def read_config():
    """Look for GUITARFLASH env variable or ~/.config/guitarflash/*.conf
       for a list of chords to show.
       Return a list of chord name strings,
       defaulting to CHORD_GROUPS['beginner'].
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

    return CHORD_GROUPS['beginner']


if __name__ == '__main__':
    # test_main()

    parser = argparse.ArgumentParser(description="Guitar Flashcards")
    parser.add_argument('-c', "--chord_test", action="store_true",
                        help="Test the user on knowledge of chords")
    parser.add_argument('-n', "--note_test", action="store_true",
                        help="Test the user on knowledge of individual notes")
    parser.add_argument('-p', "--progressions", action="store_true",
                        help="Test the user on chord progressions")
    parser.add_argument('-C', "--use-chords", default=None, action="store",
                        help="chords to use, comma or space separated "
                        "you can also specify them in "
                        "GUITARFLASH env variable or "
                        "XDG_CONFIG_HOME/guitarflash/*.conf")
    parser.add_argument('-s', "--show-chords", default=False,
                        action="store", nargs='?',
                        help="Just print the chord charts, no flashcards")
    parser.add_argument('-m', "--bpm", "--metronome",
                        action="store", default=0, dest="bpm", type=int,
                        help='Metronome Beats per Minute')
    parser.add_argument('-v', "--volume",
                        action="store", default=1, dest="volume", type=float,
                        help='Volume (a decimal, 1 = full volume)')
    parser.add_argument("--allow-sharps", action="store_true", default=False,
                        help="Include sharps in the notes to be tested")

    parser.add_argument("--csong", action="store_true", default=False,
                        help="Compose a random song in the key of C")
    parser.add_argument("--struct", action="store", default="",
                        help="Structure of the song to be composed, e.g. AABAB")

    args, rest = parser.parse_known_args(sys.argv[1:])
    Volume = args.volume

    # print("args:", args, "rest:", rest)

    if not args.chord_test and not args.note_test and not args.csong \
       and not args.show_chords and not args.progressions:
        args.show_chords = True
        print("No command specified: defaulting to showing chords")

    initialize()

    if args.progressions:
        try:
            test_chord_progressions()
        except KeyboardInterrupt:
            sys.exit(0)

    # Get a list of chords to use, otherwise, show just beginner chords
    if args.use_chords:
        chords = re.split(r"\s+|,", args.use_chords)
        for ch in rest:
            chords.append(ch)
    elif args.show_chords:
        if args.show_chords != True:
            chords = re.split(r"\s+|,", args.show_chords)
        else:
            chords = []
        for ch in rest:
            chords.append(ch)
    else:
        chords = read_config()

    chords = sanity_check_chords(chords)

    if not chords:
        if args.use_chords or args.show_chords or rest:
            print("No known chords specified")
            sys.exit(1)
        print("No known chords specified; defaulting to beginner chords")
        chords = CHORD_GROUPS['beginner']

    if args.csong:
        random_c_song(num_chords=4, delaysec=2, structure=args.struct)
            # XXX eventually other args should be settable too
        sys.exit(0)

    # Just showing, no flashcard test?
    if args.show_chords:
        display_chords_compactly(chords)
        sys.exit(0)

    if args.bpm:
        start_metronome(args.bpm)

    print(args.chord_test, args.note_test)
    try:
        while True:
            if args.chord_test and args.note_test:
                if random.randint(0, 1):
                    chord_flashcard(chords=chords)
                else:
                    note_flashcard(allow_sharps=args.allow_sharps)
            elif args.chord_test:
                chord_flashcard(chords=chords)
            elif args.note_test:
                note_flashcard(allow_sharps=args.allow_sharps)

    except KeyboardInterrupt:
        print("Bye!")
        stop_metronome()
        sys.exit()

