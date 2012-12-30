#!/usr/bin/env python

import sys, os
import termios, fcntl   # For non-blocking key reads
import time

class KeyReader :
    '''
    Read keypresses one at a time, without waiting for a newline.
    Uses the technique from
    http://docs.python.org/2/faq/library.html#how-do-i-get-a-single-keypress-at-a-time
    '''
    def __init__(self, echo=False) :
        '''Put the terminal into cbreak and noecho mode.'''
        self.fd = sys.stdin.fileno()

        self.oldterm = termios.tcgetattr(self.fd)
        newattr = termios.tcgetattr(self.fd)
        newattr[3] = newattr[3] & ~termios.ICANON
        if not echo :
            newattr[3] = newattr[3] & ~termios.ECHO
        termios.tcsetattr(self.fd, termios.TCSANOW, newattr)

        self.oldflags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.oldflags | os.O_NONBLOCK)

        # Sad hack: when the destructor __del__ is called,
        # the fcntl module may already be unloaded, so we can no longer
        # call fcntl.fcntl() to set the terminal back to normal.
        # So just in case, store a reference to the fcntl module,
        # and also to termios (though I haven't yet seen a case
        # where termios was gone -- for some reason it's just fnctl).
        # The idea of keeping references to the modules comes from
        # http://bugs.python.org/issue5099
        # though I don't know if it'll solve the problem completely.
        self.fcntl = fcntl
        self.termios = termios

    def __del__(self) :
        '''Reset the terminal before exiting the program.'''
        self.termios.tcsetattr(self.fd, self.termios.TCSAFLUSH, self.oldterm)
        self.fcntl.fcntl(self.fd, self.fcntl.F_SETFL, self.oldflags)

    def getch(self) :
        '''Read keyboard input, returning a string.
           Note that one key may result in a string of more than one character,
           e.g. arrow keys that send escape sequences.
           There may also be multiple keystrokes queued up since the last read.

           This function, sadly, cannot read special characters like VolumeUp.
           They don't show up in ordinary CLI reads -- you have to be in
           a window system like X to get those special keycodes.
        '''
        try:
            return sys.stdin.read()
        except IOError:
            return None

if __name__ == "__main__" :
    readkey = KeyReader()
    while True :
        time.sleep(1)
        c = readkey.getch()
        if not c :
            continue

        # Examples of how to compare strings.
        if c == 'q' :
            print "Bye!"
            #readkey.reset()
            readkey = None
            sys.exit(0)
        if c == '\x1b[A' :   # Up arrow
            print "Up!"
            continue

        for cc in c :
            o = ord(cc)
            if o < 32 : cc = ' '    # Don't try to print nonprintables
            print '%c (%d)' % (cc, o),
        print


