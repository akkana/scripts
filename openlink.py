#!/usr/bin/env python3

"""Open a URL in a general-purpose Firefox window,
   ignoring small windows that might be used for specific purposes
   like social networking or chat.

   Copyright 2023 by Akkana Peck: Share and enjoy under the GPLv2 or later.
"""


import sys, os
import subprocess
import time


def open_in_existing_firefox(url, minwidth=800):
    """Find the oldest firefox window that's bigger than minwidth pixels
       and open a URL in it using xdotool events.
    """
    def find_biggest_firefox_window_and_desktop():
        maxwidth = 0
        biggest_win = (None, None)
        proc = subprocess.run(["wmctrl", "-l", "-G"], capture_output=True)
        for line in proc.stdout.splitlines():
            if not line.endswith(b'irefox'):
                continue
            words = line.split()
            windowid = words[0]
            desktop = words[1]
            w = int(words[4])
            if w < minwidth:
                continue
            if w > maxwidth:
                maxwidth = w
                biggest_win = (windowid, desktop, w)

        return biggest_win

    # Find the widest firefox window
    windowid, desktop, winwidth = find_biggest_firefox_window_and_desktop()
    if not windowid:
        print("Can't find a firefox process")
        return False

    # Switch to appropriate desktop if needed
    if desktop:
        subprocess.call(['wmctrl', '-s', desktop])
        # This sometimes doesn't finish in time, and part of the text
        # ends up in the wrong window. So delay slightly:
        time.sleep(.5)

    # Move mouse to center of urlbar (winwidth/2)
    subprocess.call(['xdotool', 'mousemove', '--window', windowid,
                     f'{winwidth/2}', '75'])
    time.sleep(.3)

    # Open a new tab
    subprocess.call(['xdotool', 'keydown', 'Ctrl', 'keydown', 't',
                     'keyup', 't', 'keyup', 'Ctrl'])
    time.sleep(.3)

    # insert url
    subprocess.call(['xdotool', 'type', url])
    time.sleep(.1)

    # hit Enter to go there
    subprocess.call(['xdotool', 'keydown', 'Return', 'keyup', 'Return'])

    # Return apparent success
    return True


def quit(event):
    print("Quitting")
    sys.exit(0)


if __name__ == '__main__':
    for url in sys.argv[1:]:
        open_in_existing_firefox(url)


