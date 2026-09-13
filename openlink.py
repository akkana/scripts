#!/usr/bin/env python3

"""Open a URL in the largest Firefox window on the system,
   ignoring small windows that might be used for specific purposes
   like social networking or chat.

   Copyright 2023,2026 by Akkana Peck: Share and enjoy under the GPLv2 or later.
"""

import sys, os
import subprocess
import time
import re


# You may want to do something special with certain links, like open them
# in a different app or a different browser profile instead of doing this
# "find the biggest browser window" thing.
# If so, set up ~/.config/openlink/openlink.conf with lines like:
# https://facebook.com = safebrowser --profile fb $1
# where the pattern will be read as a regular expression
# (which can occur anywhere in the URL),
# and $1 will be replaced with the URL.
CONFIGFILE = os.path.expanduser('~/.config/openlink/openlink.conf')
special_browsers = {}
try:
    with open(CONFIGFILE) as fp:
        for line in fp:
            if line.startswith ('#'):
                continue
            line = line.split('#')[0]
            try:
                browserpat, browser = [ s.strip() for s in line.split('=') ]
                special_browsers[browserpat] = browser
            except Exception as e:
                print(f"Couldn't parse '{line}':", e, file=sys.stderr)

    print("Special browsers:", special_browsers)

except Exception as e:
    print("Couldn't open", CONFIGFILE, e, file=sys.stderr)
    pass


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
            words = line.decode().split()
            windowid = words[0]
            desktop = words[1]
            title = ' '.join(words[7:])
            w = int(words[4])
            if w < minwidth:
                continue
            if w > maxwidth:
                maxwidth = w
                biggest_win = (windowid, desktop, w, title)

        return biggest_win

    # Find the widest firefox window
    windowid, desktop, winwidth, wintitle = \
        find_biggest_firefox_window_and_desktop()
    if not windowid:
        print("Can't find a firefox process")
        return False

    # Switch to the right desktop, raise the window, and give it focus.
    # wmctrl needs flags to be separate, -ai doesn't work.
    # print("Calling wmctrl -i -a %s" % windowid)
    subprocess.run(['wmctrl', '-i', '-a', windowid])
    time.sleep(.3)

    # Move mouse to center of urlbar (winwidth/2)
    subprocess.run(['xdotool', 'mousemove', '--window', windowid,
                     f'{winwidth/2}', '75'])
    time.sleep(.3)

    # Open a new tab
    subprocess.run(['xdotool', 'keydown', 'Ctrl', 'keydown', 't',
                     'keyup', 't', 'keyup', 'Ctrl'])
    time.sleep(.3)

    # insert url
    print("typing", url)
    subprocess.run(['xdotool', 'type', url])
    time.sleep(.1)

    # hit Enter to go there
    subprocess.run(['xdotool', 'keydown', 'Return', 'keyup', 'Return'])

    # Return apparent success
    return True


def quit(event):
    print("Quitting")
    sys.exit(0)


if __name__ == '__main__':
    for url in sys.argv[1:]:
        if '://' not in url and os.path.exists(url):
            print(url, "is a file")
            url = 'file://' + os.path.abspath(url)
            print("substituting url:", url)

        for pat in special_browsers:
            if re.search(pat, url):
                if '$1' in special_browsers[pat]:
                    args = special_browsers[pat].replace('$1', url).split()
                else:
                    args = special_browsers[pat].split().append(url)
                print('args:', args)
                subprocess.run(args)
                sys.exit(0)

        open_in_existing_firefox(url)

