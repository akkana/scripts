#!/usr/bin/env python

# Some Python routines to pull and push Android files via ADB,
# on Android KitKat and late that won't let you mount the filesystem
# so you can manage it in a sensible way.
# Refer to android files with the scheme  android:/path/to
# or if you're not sure where the SD card is mounted, try
# androidsd:/relative/path and it will try to find the SD card
# if it's mounted as /storage/nnnn-nnnn.
#
# Note: this isn't well tested at all. It works well enough on my
# own personal phone (Galaxy S5 running Marshmallow) but I have
# no way of testing it on other Android hardware,
# and Google seems to love to change everything completely with every release.
# I'm happy to take patches or bug reports if you use it on other
# Android devices, and I'd love to hear where it does and doesn't work.
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
    print "Trying to list", path
    lenpath = len(path)
    print "lenpath:", lenpath

    if recursive:
        args = ["adb", "shell", "ls", "-lR", path]
    else:
        args = ["adb", "shell", "ls", "-l", path]

    proc = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE)
    stdout_lines = proc.communicate()[0].split('\n')
    file_list = []
    cur_subdir = ''
    for l in stdout_lines:
        l = l.strip()
        if not l:
            continue

        # In recursive mode, each directory will be listed with a colon.
        if recursive and l.endswith(':'):
            cur_subdir = l[:-1]
            continue

        l = l.split()
        nwords = len(l)
        if not nwords:
            continue
        elif nwords == 7:
            fname = l[-1]
            if recursive and cur_subdir:
                fname = posixpath.normpath(posixpath.join(cur_subdir, fname))[lenpath:]
                # Dependng on whether the original path ended with a slash,
                # fname might incorrectly start with one
                # because lenpath might be too small by one.
                if fname.startswith('/'):
                    fname = fname[1:]
            if sizes:
                try:
                    file_list.append((fname, int(l[3])))
                except:
                    # This could happen for the initial "Total:" line
                    pass
            else:
                file_list.append(fname)
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
    lenpath = len(path)
    if recursive:
        file_list = []
        for root, dirs, files in os.walk(path):
            root = os.path.normpath(root)
            for f in files:
                f = os.path.normpath(f)
                file_list.append(os.path.join(root, f)[lenpath:])

    else:
        file_list = os.listdir(path)

    if sorted:
        file_list.sort()

    if not sizes:
        return file_list

    # Get the size for each file.
    sizelist = []
    for filename in file_list:
        filepath = os.path.join(path, filename)
        if os.path.isdir(filepath):
            sizelist.append((filename, 0))
        else:
            try:
                sizelist.append((filename, os.stat(filepath).st_size))
            except OSError:
                sizelist.append((filename, 0))

    return sizelist

def copyto(f, outdir, fname):
    '''Copy a local file (f is the full pathname) to the android device
       at android location outdir, android new filename fname.
    '''
    subprocess.call(["adb", "push", f, posixpath.join(strip_schema(outdir),
                                                      fname)])

def find_basename_size_match(pair, pairlist):
    '''Take the basename of the given pair's first elemtn, and see if it matches
       the basename of the first element of any of the pairs in pairlist.
       If so, compare the sizes (second element), and if they match,
       return the index of the match in pairlist. Else return -1.
    '''
    base = os.path.basename(pair[0])
    for i, p in enumerate(pairlist):
        if os.path.basename(p[0]) == base:
            if p[1] == pair[1]:
                return i
            return -a
    return -1

def sync(src, dst):
    '''Synchronize recursively (like rsync -av --size-only)
       between two locations, e.g. a local directory and an android one.
       Only copy files whose size is different.
       src and dst are either a local path or an android: or androidsd: schema,
       and can point to a file or a directory.
    '''
    src_ls = list_dir(src, sorted=True, sizes=True, recursive=True)
    dst_ls = list_dir(dst, sorted=True, sizes=True, recursive=True)
    print "Found", len(src_ls), "in src,", len(dst_ls), "in dst"

    isrc = 0
    idst = 0
    updates = []    # the list of files we need to update
    removes = []
    moves = []

    while True:
        if isrc >= len(src_ls) and idst >= len(dst_ls):
            # Done with both lists!
            break

        if isrc >= len(src_ls):
            # No more src files, but there are still dst files. Remove?
            removes.append(dst_ls[idst][0])
            idst += 1
            continue

        if idst >= len(dst_ls):
            # No more dst files, but there are still src files to copy.
            updates.append(src_ls[isrc][0])
            isrc += 1
            continue

        if src_ls[isrc][0] < dst_ls[idst][0]:
            # The file exists on the src but not the dst. Need to copy.
            updates.append(src_ls[isrc][0])
            isrc += 1
            continue

        if src_ls[isrc][0] > dst_ls[idst][0]:
            # The file exists on the dst but not the src. Remove?
            # First, look to see if maybe it has moved somewhere else:
            # if its basename is somewhere else in src_ls with the same size.
            whereelse = find_basename_size_match(dst_ls[idst], src_ls)
            if whereelse < 0:
                removes.append(dst_ls[idst][0])
            else:
                # It did move! So dst_ls[idst][0] on the dst needs to move
                # to the location of src_ls[whereelse][0] on the src.
                moves.append((dst_ls[idst][0], src_ls[whereelse][0]))
            idst += 1
            continue

        if src_ls[isrc][0] == dst_ls[idst][0]:
            # The file exists on both src and dst
            if src_ls[isrc][1] != dst_ls[idst][1]:
                # the files have different sizes, need to sync.
                updates.append(ls_src[isrc][0])
            isrc += 1
            idst += 1
            continue

        print("Internal error comparing %s and %s" % (src_ls[isrc][0],
                                                      dst_ls[idst][0]))
        isrc += 1
        idst += 1

    # When setting up moves, we avoided adding the files to removes,
    # but the new location was still added to updates. Remvoe those.
    for movepair in moves:
        updates.remove(movepair[1])

    print("Need to update %d files, remove %d files, and move %d files"
          % (len(updates),  len(removes), len(moves)))
    print("======= Updates:")
    print("\n  ".join(updates))
    print("======= Removes:")
    print("\n  ".join(removes))
    print("======= Moves:")
    for movepair in moves:
        print("%s -> %s" % movepair)

def Usage():
        print("Usage:")
        print("    %s path [path ...]" % os.path.basename(sys.argv[0]))
        print("        List the given paths")
        print("    %s -s srcpath dstpath" % os.path.basename(sys.argv[0]))
        print("        Sync from srcpath to dstpath")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
        Usage()

    if len(sys.argv) == 4 and sys.argv[1] == '-s':
        sync(sys.argv[2], sys.argv[3])
        sys.exit(0)

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

