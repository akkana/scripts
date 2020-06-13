#!/usr/bin/env python3

# What directories are needed to run an app?
# Use strace to find out. Potentially useful for setting up chroots.
# Usage: dirsneeded.py cmd [arg arg ...]

'''
TODO:

>   o for anything where access attempt is made in chroot and fails,
>     at least by default, only consider it something to possibly be added
>     to chroot if that something exists outside the chroot

>   o for all opens and the like, track if it's opened for read, or
>     write/append, or both, and furthermore also track if it's only
>     read, or only written / appended to
>   o track directories accessed, and if merely accessed, or if also
>     read.  Likewise, divide and conquer, do any tests fail if read
>     access is removed, likewise to then have x removed, or directory
>     removed.

'''

import subprocess
from pathlib import Path
from collections import defaultdict
import shlex
import sys

def strace_cmd(cmdargs):
    """Run cmdargs (a list containing a command and all arguments)
       under strace, and output a list of files and directories opened.
       Returns a dict of lists of fileinfo dicts.
        { "dirpath", [ ("filename": "/tmp/foo", "mode": "O_RDONLY", etc... ] }
    """

    '''Some sample strace out lines:
openat(AT_FDCWD, "/etc/ld.so.preload", O_RDONLY|O_CLOEXEC) = 3
execve("/usr/bin/ls", ["ls", "/tmp/foo"], 0x7ffe05c05678 /* 50 vars */) = 0
access("/etc/ld.so.preload", R_OK)      = 0
statfs("/sys/fs/selinux", 0x7ffdf3e99420) = -1 ENOENT (No such file or directorystat("/tmp/moncycle", {st_mode=S_IFREG|0664, st_size=183, ...}) = 0
lstat("/tmp/moncycle", {st_mode=S_IFREG|0664, st_size=183, ...}) = 0
    '''

    cmdargs = ["strace", "-e", "trace=file"] + cmdargs

    straceout = subprocess.run(cmdargs,  # stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE).stderr.decode()

    dirlist = defaultdict(dict)

    for line in straceout.split('\n'):
        # For now, only parse the openat lines.
        if line.startswith("openat("):
            # An strace open line looks like:
            # openat(AT_FDCWD, "/lib/x86_64-linux-gnu/libc.so.6", O_RDONLY|O_CLOEXEC) = 3
            # openat(AT_FDCWD, "/tmp/foo", O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)
            # Use shlex since the filename is quoted and may include spaces.
            parts = shlex.split(line.strip())

            # but they all end with commas, so strip those.
            for i, p in enumerate(parts):
                if p.endswith(','):
                    parts[i] = p[:-1]

            fileinfo = {}
            fileinfo["filename"] = parts[1]
            fileinfo["syscall"] = parts[0]
            fileinfo["mode"] = parts[2]
            if fileinfo["mode"][-1] == ')':
                # Remove the close-paren
                fileinfo["mode"] = fileinfo["mode"][:-1]
            # Seems like I've seen additional args after the mode,
            # but now that I look, I can't find any examples.

            # Skip forward to the = to get the return value.
            # Really only need to search from parts[3] on,
            # but that messes up i.
            for i, part in enumerate(parts):
                if part == "=":
                    fileinfo["retval"] = ' '.join(parts[i+1:])
                    break

        else:
            fileinfo = None

        if fileinfo:
            # We have a filename. Find the file's directory
            path = Path(fileinfo["filename"]).resolve()
            if path.is_dir():
                dirname = str(path)
                fileinfo["type"] = "d"
            else:
                dirname = str(path.parent)

            dirlist[dirname][fileinfo["filename"]] = fileinfo

    return dirlist


def fileinfo_to_str(fileinfo):

    s = fileinfo["filename"]
    if "type" in fileinfo and fileinfo["type"] == "d":
        s += " (DIRECTORY)"
    if "mode" in fileinfo:
        s += "    (" + fileinfo["mode"] + ")"
    if "retval" in fileinfo:
        s += "    -> " + fileinfo["retval"]
    return s


if __name__ == '__main__':
    dirlist = strace_cmd(sys.argv[1:])

    for d in dirlist:
        print(d)
        files = sorted(dirlist[d].keys())
        for f in files:
            print("   ", fileinfo_to_str(dirlist[d][f]))


