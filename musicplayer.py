#! /usr/bin/env python

import sys, os
import time
import random

from pygame import mixer
import gtk, gobject

class MusicWin(gtk.Window) :
    def __init__(self, init_songs):
        super(MusicWin, self).__init__()

        self.mainbox = gtk.Table(rows=2, columns=2)
        self.add(self.mainbox)
 
        self.songs = []
        self.song_ptr = 0
        for s in init_songs:
            if os.path.isdir(s):
                # XXX Recursively crawl the directory and add every song in it.
                print "Sorry, can't do directories yet"
            else:
                self.songs.append(s)

        # Play music in random order:
        random.seed(os.getpid())
        random.shuffle(self.songs)

        mixer.init()

    def run(self):
        print "run"
        self.connect("delete_event", gtk.main_quit)
        self.connect("destroy", gtk.main_quit)
        # self.winsig = self.connect("configure_event", self.configure_event)

        self.show_all()

        # set a timeout
        gobject.timeout_add(500, self.timer_func)

        gtk.main()

    def timer_func(self):
        # Are we still playing the same song?
        if mixer.music.get_busy():
            print "\r", int(mixer.music.get_pos()/1000), " ",
            sys.stdout.flush()
            return True

        # Else time to play the next song.
        print "Playing song:", self.songs[self.song_ptr]
        mixer.music.load(self.songs[self.song_ptr])
        self.song_ptr = (self.song_ptr + 1) % len(self.songs)
        mixer.music.play()
        return True

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print "Usage:", sys.argv[0], "files or directories"
        sys.exit(1)

    rc = os.fork()
    if not rc:
        win = MusicWin(sys.argv[1:])
        win.run()
    else:
        sys.exit(0)

# Other things we can do once we have a UI:
# mixer.set_volume(.9)
# mixer.music.pause()


