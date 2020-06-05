#!/usr/bin/env python3

# hotdog: watch the temperature, and when it gets near critical,
# suspend any CPU-intensive process.

import subprocess
import json
import re
import psutil
from pprint import pprint
import sys
import time

def fetch_temps():
    temps = []
    sensors = psutil.sensors_temperatures()
    for thing in sensors:
        for piece in sensors[thing]:
            tcurrent = piece.current
            tmax = piece.high
            tcrit = piece.critical

            if not (tcurrent and (tmax or tcrit)):
                continue
            if not tmax:
                tmax = tcrit
            elif not tcrit:
                tcrit = tmax
            temps.append((thing, tcurrent, tmax, tcrit))

    print(temps)
    return temps

# import random
def overtemp(temps):
    """Are any of the temperatures excessive?
    """
    # if random.randint(0, 5) == 0:
    #     return True

    return any(quad[1] > quad[2] for quad in temps)

def hoglist(delay=3):
    """Return a list of processes using a nonzero CPU percentage
       during the interval specified by delay (seconds),
       sorted so the biggest hog is first.
    """
    proccesses = list(psutil.process_iter())
    for proc in proccesses:
        proc.cpu_percent(None)    # non-blocking; throw away first bogus value

    print("Sleeping ...")
    sys.stdout.flush()
    time.sleep(delay)
    print()

    procs = []
    for proc in proccesses:
        # Even on simple things like name(), psutil may fail with NoSuchProcess
        try:
            percent = proc.cpu_percent(None)
            if percent:
                procs.append((proc.name(), percent, proc))
        except psutil._exceptions.NoSuchProcess:
            continue

    procs.sort(key=lambda x: x[1], reverse=True)
    return procs

def slowdown(proc):
    print("\07\07Suspending process %d, '%s'" % (proc.pid, proc.name()))
    proc.suspend()

def check_and_slow(verbose=True):
    immune = [ 'Xorg', 'kworker', 'kthread', 'openbox', 'watchdog' ]
    temps = fetch_temps()

    if verbose:
        print("Temps")
        for quad in temps:
            print("%15s: %f (%f max, %f crit)" % quad)

    if overtemp(temps):
        print("Yikes! Overtemp!")

        hogs = hoglist()
        if verbose:
            print("Procs")
            for p in hogs:
                print("%20s: %5.2f" % (p[0], p[1]))

        # Slow down anything over 80%;
        # if none, then slow down the single biggest disk hog.
        if hogs[0][1] > .8:
            for h in hogs:
                if h[1] > .9:
                    slowdown(h[2])
                else:
                    break
        else:
            slowdown(hogs[0][2])

    elif verbose:
        print("Not overtemp")

if __name__ == '__main__':
    while True:
        check_and_slow()
        time.sleep(3)
