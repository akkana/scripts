#!/usr/bin/env python3

# Some Python routines to pull and push Android files via ADB,
# on Android KitKat and late that won't let you mount the filesystem
# so you can manage it in a sensible way.
# Refer to android files with the scheme  android:/path/to
# or if you're not sure where the SD card is mounted, try
# androidsd:/relative/path and it will try to find the SD card
# if it's mounted as /storage/nnnn-nnnn.
#
# Note: this isn't well tested at all and is super brittle.
# Be sure to test it on small directories before using it for
# any major copies.
# I'm happy to take patches or bug reports if you use it on other
# Android devices, and I'd love to hear where it does and doesn't work.
#
# Copyright 2017,2018 by Akkana; share and enjoy under the GPL v2 or later.

# XXX TO DO: Fix detection of empty directories and call rmdir.

import sys, os
import subprocess
import posixpath
import shutil
import pipes
import re
import argparse

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
            raise RuntimeError("Can't access Android device")
        return '/storage/' + sdcards[0] + '/' + path[10:]

    return path

def find_sdcards():
    sdcards = []
    proc = subprocess.Popen(["adb", "shell", "ls", "/storage"],
                            shell=False,
                            stdout=subprocess.PIPE)
    stdout_lines = proc.communicate()[0].decode().split('\n')
    sdpat = re.compile('[0-9A-F]{4}-[0-9A-F]{4}')
    for line in stdout_lines:
        m = sdpat.search(line)
        if not m:
            continue
        sdcards.append(line[m.start():m.end()])
    return sdcards

def list_dir(path, **kwargs):
    '''Recursively list either a local or remote directory.
       Return a list of paths relative to the original directory.
    '''
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
    stdout_lines = proc.communicate()[0].decode().split('\n')
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
                # XXX Next line had lenpath-1: instead of lenpath.
                # For running on androidsd:path/to or androidsd:/path/to,
                # lenpath is correct. Is there a case where lenpath-1 is?
                fname = posixpath.normpath(posixpath.join(cur_subdir,
                                                          fname))[lenpath:]

                # Depending on whether the original path ended with a slash,
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
    path = os.path.normpath(path)
    lenpath = len(path)
    if recursive:
        file_list = []
        for root, dirs, files in os.walk(path):
            root = os.path.normpath(root)
            for f in files:
                # Get rid of anything like ./ at the beginning
                f = os.path.normpath(f)

                if root == '.':
                    file_list.append(f)
                else:
                    # Include the necessary part of the file's path,
                    # but omit the root we started from.
                    fpath = os.path.join(root, f)

                    # This is a bit tricky. fpath includes root
                    # which includes the original path, and we need to
                    # remove that part of it in the file list;
                    # but if the original path was ., the ./ isn't
                    # in fpath because os.normpath() removed it.
                    if path != '.':
                        fpath = fpath[lenpath+1:]
                    file_list.append(fpath)

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
            except OSError as e:
                print("OSError on", filepath, "path was", path)
                print(e)
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
        os.makedirs(d, exist_ok=True)

def remove(f):
    if is_android(f):
        remove_from_android(strip_schema(f))
    else:
        os.unlink(f)

def find_basename_size_match(pair, pairlist):
    '''Given a pair (pathname, size) and a list of pairs, take the basename
       of the given pair's first elemend, and see if it matches
       the basename of the first element of any of the pairs in pairlist.
       If so, compare the sizes (second element), and if they match,
       return the index of the match in pairlist. Else return -1.
       If there's more than one match, be safe and return -1:
       in that case we can't rely on size.
    '''
    base = os.path.basename(pair[0])
    match = None
    num_matches = 0
    for i, p in enumerate(pairlist):
        if os.path.basename(p[0]) == base:
            if p[1] == pair[1]:
                match = i
                num_matches += 1
    if num_matches == 1:
        return match
    elif num_matches > 1:
        print("Multiple matches for", base)
    return -1

def make_sync_changes(newdirs, moves, removes, updates, dryrun):
    '''Print the sync changes, and, if dryrun is false, actually make them.
    '''
    if newdirs:
        if dryrun:
            print("\n\nMaking needed directories")
        for d in newdirs:
            if dryrun:
                print("mkdir " + d)
            else:
                mkdir(d)
    else:
        print("No new directories to make.")

    if moves:
        if dryrun:
            print("\n\nMoving files that changed location but not size")
        for mvsrc, mvdst in moves:
            if dryrun:
                print("%s -> %s" % (mvsrc, mvdst))
            else:
                move(mvsrc, mvdst)
    else:
        print("No files need moving.")

    if removes:
        if dryrun:
            print("\n\nRemoving files that are no longer needed on the dst")
        for rm in removes:
            if dryrun:
                print(rm)
            else:
                remove(rm)
    else:
        print("No files need removing.")

    if updates:
        if dryrun:
            print("\n\nCopying files that are new or changed")
        for pair in updates:
            if dryrun:
                print(" %s ->\n   %s" % pair)
            else:
                copyfile(*pair)
    else:
        print("No files need updating.")

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

    # Indices as we loop over the src and dst lists:
    isrc = 0
    idst = 0

    # The list of files we need to update, remove or move:
    updates = []
    removes = []
    moves = []
    newdirs = []

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
                updates.append(src_ls[isrc][0])
            isrc += 1
            idst += 1
            continue

        print("Internal error comparing %s and %s" % (src_ls[isrc][0],
                                                      dst_ls[idst][0]))
        isrc += 1
        idst += 1

    # When setting up moves, we avoided adding the files to removes,
    # but the new location was still added to updates. Remove those.
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
    for d in dstdirs:
        d = dst + d

        # XXX Somehow these are coming out /path/to/dirname/.
        # As a temporary fix, remove the final /.
        if d.endswith('/.'):
            d = d[:-2]

        if not is_android(d) and os.path.exists(d):
            continue
        # XXX Should check our file list to see if it exists if it's android.

        newdirs.append(d)

    # Add the full paths to the move pairs.
    briefmoves = moves
    moves = []
    for movepair in briefmoves:
        # These are both paths on the dst.
        moves.append((dst + movepair[0], dst + movepair[1]))

    # Then the full paths for the removes.
    briefremoves = removes
    removes = []
    for rm in briefremoves:
        rm = dst + rm
        removes.append(rm)

    # Finally, the updates.
    srclen = len(src)

    # Special case: if we're syncing from ./ it will have been stripped
    # from the destination path, so those are two more characters we
    # won't need to remove from dstup.
    # XXX Be smarter about translating up to dstup, making sure to
    # change only the src->dst paths.
    if src.startswith('./'):
        srclen -= 2
    briefupdates = updates
    updates = []
    for up in briefupdates:
        updates.append((src + up, dst + up))

    #
    # Finally, all the lists are made.
    # Call make_sync_changes, first to print the proposed changes
    # and then to do them (if not a dryrun).
    #

    make_sync_changes(newdirs, moves, removes, updates, dryrun=True)
    if dryrun:
        print("\nThat's would have changed, if this wasn't a dry run.")
        return

    if not newdirs and not moves and not removes and not updates:
        print("Nothing to do.")
        return

    ans = input("Make changes? (y) ")
    if ans.lower().startswith('n'):
        return

    make_sync_changes(newdirs, moves, removes, updates, dryrun=False)


def Usage():
    progname = os.path.basename(sys.argv[0])
    return ("""%s: list or sync directories with Android over adb.

Usage:
    %s path [path ...]
        List the given paths"
    %s -s [-n] srcpath dstpath
        Sync from srcpath to dstpath

    Paths may be local files, android:/path/to, or androidsd:/path/to."""
        % (progname, progname, progname))

def parse_args():
    """Parse commandline arguments."""
    parser = argparse.ArgumentParser(usage=Usage(),
                                     description="List or sync files between Linux and Android")

    parser.add_argument('-n', "--dryrun", dest="dryrun", default=False,
                        action="store_true")
    # Doesn't currently work without recursive,
    # but might eventually want to make that optional.
    # parser.add_argument('-r', "--recursive", dest="recursive", default=False,
    #                     action="store_true")
    parser.add_argument('-s', "--sync", dest="sync", default=False,
                        action="store_true")
    parser.add_argument('-z', "--no-size", dest="nosize", default=False,
                        action="store_true")
    parser.add_argument("paths", nargs='+')

    args = parser.parse_args()

    # I can't find a way to get argparse to handle this.
    if args.sync and len(args.paths) != 2:
        print("-s must have exactly 2 parameters, src and dst\n")
        print(Usage())
        sys.exit(2)

    return args

def main():

    args = parse_args()
    # print(args)

    if args.sync:
        sync(args.paths[0], args.paths[1], dryrun=args.dryrun)
        return

    for path in (args.paths):
        print("\n%s :" % path)
        files = list_dir(path, sizes=(not args.nosize), recursive=True)
        if not args.nosize:
            for f in files:
                if f[1] < 500:
                    print("%d\t%s" % (f[1], f[0]))
                else:
                    print("%dk\t%s" % (int((f[1]+500)/1000), f[0]))
        else:
            print("%s: %s" % (path, ', '.join(files)))

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(str(e))
