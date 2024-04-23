#!/usr/bin/env python3

# Generate a random geometry specifier, like 165x65+142-298
# for apps that are always visible (like dclock) and need to be moved
# around to avoid monitor burn-in.

# Usage: randomgeom appsize side-vs-top top-vs-bottom
# appsize: WIDTHxHEIGHT
# side-vs-top: the percent likelihood of sticking the app along the
#              top or bottom of the monitor rather than the side
# top-vs-bottom: percent liklihood of being on the top edge vs. bottom.

from random import randint
from sys import argv, exit
import subprocess


def random_geometry():
    appsize = argv[1]
    appwidth, appheight = map(int, appsize.split('x'))
    side_vs_top = int(argv[2])
    top_vs_bottom = int(argv[3])

    # Get the monitor size from xdpyinfo
    monwidth = None
    proc = subprocess.run(["xdpyinfo"], capture_output=True)
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith(b"dimensions:"):
            continue
        dimensions = line.split()[1]
        monwidth, monheight = map(int, dimensions.split(b'x'))
    if not monwidth:
        print("Couldn't get monitor dimensions")
        exit(1)

    # Side vs. top
    if randint(0, 100) < side_vs_top:
        # top or bottom. Either way, calculate X coordinate:
        x = randint(0, monwidth - appwidth)
        if randint(0, 100) < top_vs_bottom:
            # top
            return f'{appsize}+{x}+0'
        else:
            # bottom
            return f'{appsize}+{x}-0'

    else:
        # sides. Calculate y coordinate:
        y = randint(0, monheight - appheight)
        # left or right?
        if randint(0, 1):
            # left
            return f'{appsize}+0+{y}'
        else:
            # right
            return f'{appsize}-0+{y}'


if __name__ == '__main__':
    try:
        print(random_geometry())
    except RuntimeError:
        from os.path import basename
        print(f"Usage: {basename(argv[0])} appsize side-vs-top top-vs-bottom")
        print(f"    e.g. {basename(argv[0])} 165x65 50 50")
        exit(1)

