#!/usr/bin/env python

# Get the current size of the terminal window, and set stty size accordingly.
# A replacement for xterm's resize program, with no X dependency.
# Useful when logged in over a serial line.
# Copyright 2013 by Akkana Peck -- share and enjoy under the GPL v2 or later.

# In the unlikely event you ever need to *set* the terminal size, check out:
# https://github.com/zerorax/pyresize/blob/master/resize.py

import os, sys
import fcntl
import posix
import struct
import time
import re
import termios
import select

fd = sys.stdin.fileno()

# python3 has get_terminal size. Yay!
if hasattr(os, 'get_terminal_size'):
    cols, rows = os.get_terminal_size()

# python2 does not.
else:
    tty = open('/dev/tty', 'r+')
    tty.write('\033[7\033[r\033[999;999H\033[6n')
    tty.flush()

    oldterm = termios.tcgetattr(fd)
    newattr = oldterm[:]
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

    try:
        while True:
            r, w, e = select.select([fd], [], [])
            if r:
                output = sys.stdin.read()
                break
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

    rows, cols = list(map(int, re.findall(r'\d+', output)))

fcntl.ioctl(fd, termios.TIOCSWINSZ,
            struct.pack("HHHH", rows, cols, 0, 0))

print("\nReset the terminal to %d rows, %d cols" % (rows, cols))






