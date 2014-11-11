#!/usr/bin/env python

import curses
import time
import sys

errstr = ''

numwidth = 5
fmt = '%%%dd' % numwidth

stdscr = curses.initscr()
curses.noecho()
curses.cbreak()
#if curses.can_change_color():
if curses.has_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
    colorpair = curses.color_pair(1)
    highlightpair = curses.color_pair(2)
else:
    colorpair = curses.A_REVERSE
    highlightpair = curses.A_BOLD

def cleanup():
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()

    if errstr:
        print "Errors:", errstr
    sys.exit(0)

height, width = stdscr.getmaxyx()
width -= numwidth+1
height -= 1

# How many numbers will fit on a line, or on the whole screen?
numsperline = int(width / numwidth)
maxnum = numsperline * height

attributes = [0] * (maxnum+2)

logf = open("/tmp/sieve.log", "w", buffering=1)
print >>logf, "Maxnum is", maxnum

def redraw_screen(highlight=None):
    num = 0
    while True:
        num += 1
        x = ((num-1) % numsperline) * numwidth
        y = int ((num-1) / numsperline)
        if y >= height:
            return

        if x < numwidth:
            print >>logf, ".\n"
        print >>logf, "'%s' @ (%d, %d) " % (fmt % num, x, y),
        #errstr += "'%s' @ (%d, %d) " % (fmt % num, x, y)
        #errstr += "\nstdscr.addstr(%d, %d, '%s')" % (y, x, fmt % num)
        if highlight == num:
            stdscr.addstr(y, x, fmt % num, highlightpair)
        else:
            stdscr.addstr(y, x, fmt % num, attributes[num])

    stdscr.refresh()
    print >>logf, "Refreshed"
    return num

try:
    key = None
    divisor = 1

    while key != ord('q'):
        # Skip past known composites to the next prime:
        divisor += 1
        while attributes[divisor]:
            divisor += 1
            print >>logf, "divisor++ to", divisor
        print >>logf, divisor, "is prime"

        for i in xrange(1, maxnum):
            if i > divisor and i % divisor == 0:
                print >>logf, "Setting attribute for", i
                attributes[i] = colorpair

        print >>logf, "Finished setting attributes for", divisor

        redraw_screen(highlight=divisor)
        key = stdscr.getch()
        
except Exception, e:
    errstr += "Exception: " + str(e)

finally:
    # Don't have to call cleanup() -- it'll be called magically
    cleanup()
