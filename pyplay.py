#! /usr/bin/env python

# A class to play sounds asynchronously, but not overlapping.
#
# Copyright 2012 by Akkana Peck, http://shallowsky.com.
# Share and enjoy under the GPLv2 or (at your option) any later version.

from __future__ import print_function

import sys
import subprocess

class SoundPlayer :
    """
       Play sounds that don't overlap in time.
    """

    PLAYER = "/usr/bin/aplay"

    def __init__(self) :
        self.curpath = None
        self.current = None

    def __del__(self) :
        print("__del__ : Waiting for last play")
        self.wait()

    def play(self, path) :
        if self.current :
            if self.current.poll() == None :
                # Current process hasn't finished yet. Is this the same sound?
                if path == self.curpath :
                    # A repeat of the currently playing sound.
                    # Don't play it more than once.
                    print(path, "is still playing. Not playing again")
                    return
                else :
                    # Trying to play a different sound.
                    # Wait on the current sound then play the new one.
                    print("Different sound; first waiting for", self.curpath)
                    self.wait()
            self.current = None
            self.curpath = None

        print("Trying to play", path)

        self.curpath = path
        self.current = subprocess.Popen([ SoundPlayer.PLAYER, '-q', path ] )

    def wait(self) :
        if self.current and self.current.poll() == None :
            self.current.wait()

# To test this class, run this file with a list of paths to sound files,
# and make sure to repeat some of them.
# For instance,
# pyplay.py pop.wav pop.wav pop.wav meow.wav meow.wav pop.wav pop.wav
if __name__ == "__main__" :
    if len(sys.argv) < 1 :
        print("This test doesn't make much sense without some sound arguments")
        sys.exit(1)
    player = SoundPlayer()
    for arg in sys.argv[1:] :
        player.play(arg)
    player.wait()
