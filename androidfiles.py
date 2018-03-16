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
import shutil
import pipes
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
    lenpath = len(path)

    if recursive:
        args = ["adb", "shell", "ls", "-lR", path]
    else:
        args = ["adb", "shell", "ls", "-l", path]

    proc = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE)
    stdout_lines = proc.communicate()[0].split('\n')
    file_list = []
    cur_subdir = ''
    for line in stdout_lines:
        line = line.strip()
        if not line:
            continue

        # In recursive mode, each directory will be listed with a colon.
        if recursive and line.endswith(':'):
            cur_subdir = line[:-1]
            continue

        l = line.split()
        nwords = len(l)
        if not nwords:
            continue

        if line.startswith('-rw'):
            if nwords < 7:
                print("Not enough words for a file listing: %s"% l)
                continue
            # Account for filenames with spaces: anything from element 6
            # to the end is the filename.
            fname = ' '.join(l[6:])

            if recursive and cur_subdir:
                fname = posixpath.normpath(posixpath.join(cur_subdir,
                                                          fname))[lenpath:]
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

        # elif line.startswith('drw'):
        #     print("%s is a directory" % l[-1])

        # else:
        #     print("Not a file or directory: %s" % l)

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
    print "list_local_dir", path, sorted, sizes, recursive
    lenpath = len(path)
    if recursive:
        file_list = []
        for root, dirs, files in os.walk(path):
            root = os.path.normpath(root)
            print "root", root
            for f in files:
                f = os.path.normpath(f)
                print "  appending", os.path.join(root, f)
                # What was I thinking here?
                # file_list.append(os.path.join(root, f)[lenpath+1:])
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
        filepath = os.path.normpath(os.path.join(path, filename))
        print root, path, filename
        print "filepath:", filepath
        if os.path.isdir(filepath):
            sizelist.append((filename, 0))
        else:
            try:
                sizelist.append((filename, os.stat(filepath).st_size))
                print "Got the size for", filepath
            except OSError:
                print "OSError on", filepath, "path was", path
                sizelist.append((filename, 0))
                sys.exit(0)

    return sizelist

# Helper routines to copy to/from/on android.
# These assume the schemas have already been removed.
def quote(s):
    return pipes.quote(s)

def copy_to_android(src, dst):
    subprocess.call(["adb", "push", quote(src), quote(dst)])

def copy_from_android(src, dst):
    # Copy from android to local
    subprocess.call(["adb", "pull", quote(src), quote(dst)])

def copy_on_android(src, dst):
    subprocess.call(["adb", "shell", "cp", quote(src), quote(dst)])

def move_on_android(src, dst):
    subprocess.call(["adb", "shell", "mv", quote(src), quote(dst)])

def remove_from_android(f):
    subprocess.call(["adb", "shell", "rm", quote(f)])

def mkdir_on_android(d):
    subprocess.call(["adb", "shell", "mkdir", quote(d)])

def rmdir_on_android(d, recursive=False):
    if recursive:
        subprocess.call(["adb", "shell", "rm", "-rf", quote(d)])
    else:
        subprocess.call(["adb", "shell", "rmdir", quote(d)])

####################################################################
# Here are the public routines that we expect callers to know about:
# copyfile, remove, move, mkdir
# which can take an android: or androidsd: schema or a local path.

def copyfile(src, dst, move=False):
    '''Copy src file to dst, where either or both can have
       android: or androidsd: schemas.
       Only intended to handle single files;
       doesn't create directories first.
       If move=True, use move rather than copy (remove the src).
    '''
    if not is_android(src) and not is_android(dst):
        if move:
            shutil.move(src, dst)
        else:
            shutil.copyfile(src, dst)

    elif is_android(src) and is_android(dst):
        if move:
            move_on_android(strip_schema(src), strip_schema(dst))
        else:
            copy_on_android(strip_schema(src), strip_schema(dst))

    elif is_android(src):
        srcpath = strip_schema(src)
        copy_from_android(srcpath, dst)
        if move:
            remove_from_android(srcpath)

    elif is_android(dst):
        copy_to_android(src, strip_schema(dst))
        if move:
            os.unlink(src)

    else:
        print("Internal error: couldn't figure out how to %s %s to %s"
              % ('move' if move else 'copy', src, dst))

def move(src, dst):
    copyfile(src, dst, move=True)

def mkdir(d):
    if is_android(d):
        mkdir_on_android(strip_schema(d))
    else:
        os.mkdir(d)

def remove(f):
    if is_android(f):
        remove_from_android(strip_schema(f))
    else:
        os.unlink(f)

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
            return -1
    return -1

def sync(src, dst, dryrun=True):
    '''Synchronize recursively (like rsync -av --size-only)
       between two locations, e.g. a local directory and an android one.
       Only copy files whose size is different.
       src and dst are either a local path or an android: or androidsd: schema,
       and can point to a file or a directory.
       If dryrun, just print what is to be done, don't actually do it.
       XXX: basically works but needs to remove empty directories.
    '''
    src_ls = list_dir(src, sorted=True, sizes=True, recursive=True)
    dst_ls = list_dir(dst, sorted=True, sizes=True, recursive=True)

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
        # print("Removing %s from updates, it's moving from %s"
        #       % (movepair[1], movepair[0]))
        try:
            updates.remove(movepair[1])
        except:
            # If it wasn't in updates, then it already exists in the new
            # location on the dest and doesn't need to be moved.
            # Zero out that movepair, since it's hard to remove from a list
            # while looping over that same list.
            mvoepair = None

    # Remove the entries we just nullified:
    moves = [ m for m in moves if m != None ]

    # XXX We've moved and removed files from the dst; will we be leaving
    # any empty directories behind?

    # Will we need to create any new directories?
    # First, list all the directories we'll be using.
    dstdirs = []

    def find_dir_in(thedir, whichlist):
        '''Is the given directory referenced in any of the pathnames
           in whichlist?
        '''
        # We need to end with a slash, because otherwise we might
        # match books whose titles start with the same name as the dir.
        if not thedir.endswith('/'):
            thedir += '/'
        for pair in whichlist:
            if pair[0].startswith(thedir):
                return True

        return False

    def remember_needed_dirs(f):
        '''Check full pathname f (from src_ls) to see if its dirname
           already exists in the list of directories in dst_ls.
           If it doesn't, then it will need to be created on the
           destination, perhaps along with its ancestors.
        '''
        d = os.path.dirname(f)
        if d in dstdirs:
            return
        if find_dir_in(d, dst_ls):
            return

        # The directory probably needs to be created.
        # But does any intermediate directory also need creation?
        # Append them in descending order (a/b/c before a/b/c/d)
        # since that's the order in which they need to be created.
        # This code assumes posix on both ends.
        # It probably won't work on Windows.
        components = d.split('/')
        # d itself is os.path.join(components)

        for i in range(1, len(components)):
            dd = posixpath.join(*components[0:i])
            if dd not in dstdirs and not find_dir_in(dd, dst_ls):
                dstdirs.append(dd)
        dstdirs.append(d)

    for fpair in moves:
        remember_needed_dirs(fpair[1])
    for f in updates:
        remember_needed_dirs(f)

    # Time to actually do it!

    # We'll be prepending src and dst (including their schemae)
    # so make sure they end with a slash:
    if not src.endswith('/'):
        src += '/'
    if not dst.endswith('/'):
        dst += '/'

    # Make all needed directories:
    print("\n\nMaking needed directories")
    for d in dstdirs:
        d = dst + d
        print("mkdir " + d)
        if not dryrun:
            mkdir(d)

    # Do the moves:
    print("\n\nMoving files that changed location but not size")
    for movepair in moves:
        # These are both paths on the dst.
        mvsrc = dst + movepair[0]
        mvdst = dst + movepair[1]
        print("%s -> %s" % (mvsrc, mvdst))
        if not dryrun:
            move(mvsrc, mvdst)

    # Then the removes, to make room for the new stuff:
    print("\n\nRemoving files that are no longer needed on the dst")
    for rm in removes:
        rm = dst + rm
        print(rm)
        if not dryrun:
            remove(rm)

    # Finally, the updates.
    print("\n\nCopying up files that are new or changed")
    for up in updates:
        srcup = src + up
        dstup = dst + up
        print("Updating %s -> %s" % (srcup, dstup))
        if not dryrun:
            copyfile(srcup, dstup)

    if dryrun:
        print("\nThat's what we would have done, if this wasn't a dry run")

def Usage():
    progname = os.path.basename(sys.argv[0])
    print("""%s: list or sync directories with Android over adb.

Usage:
    %s path [path ...]
        List the given paths"
    %s -s srcpath dstpath
        Sync from srcpath to dstpath

    Paths may be local files, android:/path/to, or androidsd:/path/to."""
        % (progname, progname, progname))
    sys.exit(1)

def main():
    args = sys.argv[1:]
    if not args:
        Usage()

    if args[0] == '-h' or args[0] == '--help':
        Usage()

    if args[0] == '-dryrun' or args[0] == '-n':
        dryrun = True
        args = args[1:]
    else:
        dryrun = False

    if len(args) == 3 and args[0] == '-s':
        sync(args[1], args[2], dryrun=dryrun)
        sys.exit(0)

    sizes = True
    recursive = True

    for path in (sys.argv[1:]):
        print("Listing path %s" % path)
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

if __name__ == "__main__":
    main()
