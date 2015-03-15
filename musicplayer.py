#! /usr/bin/env python

import sys, os
import time
from pygame import mixer

if len(sys.argv) < 2:
    print "Usage:", sys.argv[0], "files or directories"

songs = []
for s in sys.argv[1:]:
    if os.path.isdir(s):
        # Recursively crawl the directory and add every song in it.
        print "Sorry, can't do directories yet"
    else:
        songs.append(s)

mixer.init()

for song in songs:
    print "Loading", song
    mixer.music.load(song)
    mixer.music.play()
    while mixer.music.get_busy():
        print "\r", int(mixer.music.get_pos()/1000), " ",
        sys.stdout.flush()
        time.sleep(.25)
    print

# mixer.set_volume(.9)
# mixer.music.pause()


