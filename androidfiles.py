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
            removes.append(dst_ls[idst][0])
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

    print("Need to update %d files and remove %d files" % (len(updates),
                                                           len(removes)))
    print("======= Updates")
    print("\n  ".join(updates))
    print("======= Removes")
    print("\n  ".join(removes))

    # Before actually copying, see if it looks like something has been moved:
    # the same filename in a different directory.
    def check_for_move(changes, whichlist, whichopstr, whichliststr):
        for f in changes:
            newversion = is_in_list(f, whichlist)
            if newversion:
                # Now find it in the source list to compare sizes
                oldversion = None
                for s in src_ls:
                    if s[0] == f:
                        oldversion = s
                        break
                if not oldversion:
                    print("Internal error: %s on %s list but can't find it."
                          % (f, whichopstr))
                    continue
                if oldversion[1] == newversion[1]:
                    print("Looks like %s in %s is %s on %s"
                          % (oldversion[0], whichopstr,
                             newversion[0], whichliststr))

    check_for_move(updates, dst_ls, "updates", "dst")
    check_for_move(removes, src_ls, "removes", "src")

def is_in_list(fname, filelist):
    '''Is the given filename (a basename, not a full pathname)
       in the given list? The filelist may be a list of pathnames,
       or it may be a list of (pathname, size).
       Either way, return the matching element of filelist, or None.
    '''
    for f in filelist:
        # Is it a string-like object or a list-like object?
        # String-like objects have endswith.
        if hasattr(f, 'endswith'):
            fn = f
        else:
            fn = f[0]
        fn = os.path.basename(fn)
        # XXX This will work on *nix. On Windows, we need to use
        # os.path if it's local, posixpath if it's remote.
        # For now I'm not going to worry about that.

        if fname == fn:
            return f

    return None

if __name__ == "__main__":
    # copyto('/home/akkana/POD/Science/Story_Collider/249076872-the-story-collider-jonaki-bhattacharyya-losing-control.mp3', 'android:/mnt/extSdCard/Music/Podcasts', '16-05-99-so-special.mp3')

    if len(sys.argv) < 2:
        print("Usage: %s path [path ...]" % os.path.basename(sys.argv[0]))
        sys.exit(1)

    if len(sys.argv) == 3:
        sync(sys.argv[1], sys.argv[2])
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

