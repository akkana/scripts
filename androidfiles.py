#!/usr/bin/env python

# Some Python routines to pull and push Android files via ADB,
# on Android KitKat and late that won't let you mount the filesystem
# so you can manage it in a sensible way.
# Refer to android files with the scheme  android:/path/to
# or if you're not sure where the SD card is mounted, try
# androidsd:/relative/path and it will try to find the SD card
# if it's mounted as /storage/nnnn-nnnn.
#
# Copyright 2017 by Akkana; share and enjoy under the GPL v2 or later.

import sys, os
import subprocess
import posixpath
import re

def is_android(path):
    return path.startswith("android:") or path.startswith("androidsd:")

def strip_schema(path):
    '''Strip off any android: prefix in the path.
    '''
    if path.startswith("android:"):
        return path[8:]

    if path.startswith("androidsd:"):
        sdcards = find_sdcards()
        if not sdcards:
            return None
        return '/storage/' + sdcards[0] + '/' + path[10:]

    return path

def find_sdcards():
    sdcards = []
    proc = subprocess.Popen(["adb", "shell", "ls", "/storage"],
                            shell=False,
                            stdout=subprocess.PIPE)
    stdout_lines = proc.communicate()[0].split('\n')
    sdpat = re.compile('[0-9A-F]{4}-[0-9A-F]{4}')
    for line in stdout_lines:
        m = sdpat.search(line)
        if not m:
            continue
        sdcards.append(line[m.start():m.end()])
    return sdcards

def list_dir(path, **kwargs):
    if is_android(path):
        return list_android_dir(strip_schema(path), **kwargs)
    else:
        return list_local_dir(path, **kwargs)

def list_android_dir(path, sorted=True, sizes=False, recursive=False):
    '''List the contents of the given directory on Android.
       Returns a list of filenames if sizes=False.
       If sizes=True, returns a list of tuples (filename, int size).
       If recursive, return a list of relative paths of leaf names
       like foo/bar/baz.jpg.
    '''
    if recursive:
        print("Sorry, don't know how to do recursive list on android yet")
    print "Trying to list", path
    proc = subprocess.Popen(["adb", "shell", "ls", "-l", path],
                            shell=False,
                            stdout=subprocess.PIPE)
    stdout_lines = proc.communicate()[0].split('\n')
    file_list = []
    for l in stdout_lines:
        l = l.strip().split()
        nwords = len(l)
        if not nwords:
            continue
        elif nwords == 7:
            if sizes:
                try:
                    file_list.append((l[-1], int(l[3])))
                except:
                    # This could happen for the initial "Total:" line
                    pass
            else:
                file_list.append(l[-1])
        elif nwords == 6:
            print("%s is a directory" % l[-1])
        else:
            print("Wrong number %d of things, %s" % (nwords, l))
    if sorted:
        file_list.sort()

    return file_list

def list_local_dir(path, sorted=True, sizes=False, recursive=False):
    '''List the contents of the given local directory,
       returning the result in the same format list_android_dir would return
       so we can use them interchangeably.
       Returns a list of filenames if sizes=False.
       If sizes=True, returns a list of tuples (filename, int size).
       If recursive, return a list of relative paths of leaf names
       like foo/bar/baz.jpg.
    '''
    if recursive:
        file_list = []
        for root, dirs, files in os.walk(path):
            root = os.path.normpath(root)
            if sorted:
                files.sort()
            for f in files:
                f = os.path.normpath(f)
                file_list.append(os.path.join(root, f))

    else:
        file_list = os.listdir(path)

        if sorted:
            file_list.sort()

    if not sizes:
        return file_list

    # Get the size for each file.
    sizelist = []
    for filename in file_list:
        if os.path.isdir(filename):
            sizelist.append((filename, 0))
        else:
            try:
                sizelist.append((filename, os.stat(filename).st_size))
            except OSError:
                sizelist.append((filename, 0))

    return sizelist

def copyto(f, outdir, fname):
    '''Copy a local file (f is the full pathname) to the android device
       at android location outdir, android new filename fname.
    '''
    subprocess.call(["adb", "push", f, posixpath.join(strip_schema(outdir),
                                                      fname)])

def sync(src, dest):
    '''Synchronize recursively (like rsync -av --size-only)
       between two locations, e.g. a local directory and an android one.
       Only copy files whose size is different.
    '''

if __name__ == "__main__":
    # copyto('/home/akkana/POD/Science/Story_Collider/249076872-the-story-collider-jonaki-bhattacharyya-losing-control.mp3', 'android:/mnt/extSdCard/Music/Podcasts', '16-05-99-so-special.mp3')

    if len(sys.argv) < 2:
        print("Usage: %s path [path ...]" % os.path.basename(sys.argv[0]))
        sys.exit(1)

    sizes = True
    recursive = True

    for path in (sys.argv[1:]):
        files = list_dir(path, sizes=sizes, recursive=recursive)
        if sizes:
            print("%s:" % path)
            for f in files:
                if f[1] < 500:
                    print("%d\t%s" % (f[1], f[0]))
                else:
                    print("%dk\t%s" % (int((f[1]+500)/1000), f[0]))
        else:
            print("%s: %s" % (path, ', '.join(files)))

