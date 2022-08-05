#!/usr/bin/env python3

# Convert a hierarchy of epub ebooks in a source directory
# to a kepub hierarchy in a destination directory
# that can be copied to a Kobo e-reader,
# preserving directory structure and keeping creation and modification dates
# unchanged.

import koboize

import sys, os
import shutil

try:
    srcdir, dstdir = sys.argv[1], sys.argv[2]
except:
    print("Usage: %s srcdir dstdir" % os.path.basename(sys.argv[0]))
    sys.exit(1)

for root, dirs, files in os.walk(srcdir):

    # Get part of root that's relative to srcdir.
    if not root.startswith(srcdir):
        print(f"root '{root}' doesn't start with srcdir '{srcdir}'!",
              file=sys.stderr)
        sys.exit(1)
    relroot = root[len(srcdir):]
    while relroot.startswith('/'):
        relroot = relroot[1:]

    dstroot = os.path.join(dstdir, relroot)
    try:
        os.makedirs(dstroot)
        print("mkdir:", dstroot)
    except FileExistsError:
        print(dstroot, "already exists")
        pass

    for f in files:
        origpath = os.path.join(root, f)

        flower= f.lower()
        if not flower.endswith(".epub"):
            print("Skipping", origpath, ": not epub")
            continue

        if flower.endswith(".kepub.epub"):
            dstpath = os.path.join(dstroot, f)
            if os.path.exists(dstpath):
                print(dstpath, "already exists")
            else:
                shutil.copy2(origpath, dstpath)
                print("Copied", dstpath)
            continue

        try:
            newfilename = f[:-5] + ".kepub.epub"
            dstpath = os.path.join(dstroot, newfilename)
            if os.path.exists(dstpath):
                print(dstpath, "already exists")
            else:
                koboize.convert_file(origpath, dstroot)
            shutil.copystat(origpath, dstpath)
        except Exception as e:
            print("Couldn't convert", origpath, ":", e, file=sys.stderr)


