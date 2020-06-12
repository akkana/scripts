#!/usr/bin/env python3

# What directories are needed to run an app?
# Use strace to find out. Potentially useful for setting up chroots.
# Usage: dirsneeded.py cmd [arg arg ...]

import subprocess
import bisect
from pathlib import Path
from collections import defaultdict
import sys

def strace_cmd(cmdargs):
    """Run cmdargs (a list containing a command and all arguments)
       under strace, and output a list of files and directories opened.
    """

    cmdargs.insert(0, "strace")
    straceout = subprocess.run(cmdargs, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE).stderr

    dirlist = []
    filelist = defaultdict(set)
    for line in straceout.split(b'\n'):
        if line.startswith(b"openat("):
            # Take the string between the first and second " marks
            q1 = line.find(b'"')
            q2 = line.find(b'"', q1+1)
            if q1 <= 0 or q2 <= 0:
                raise(RuntimeError("openat line with no quotes: " + line))

            # Find the file's directory and see if it's already in the list.
            path = Path(line[q1+1:q2].decode()).resolve()
            if path.is_dir():
                filename = None
                pathstr = str(path)
            else:
                pathstr = str(path.parent)
                filelist[pathstr].add(path.name)

            # if not file_is_in_dirlist(pathstr, dirlist):
            if pathstr not in dirlist:
                # How to insert into a list keeping the list sorted
                bisect.insort(dirlist, pathstr)

    # Convert the file lists from sets to sorted lists
    for d in filelist:
        filelist[d] = list(filelist[d])
        filelist[d].sort()

    return dirlist, filelist


if __name__ == '__main__':
    dirlist, filelist = strace_cmd(sys.argv[1:])
    for d in dirlist:
        print(d)
        if d in filelist:
            print("   ", '\n    '.join(filelist[d]))


