#!/usr/bin/env python3

from koboize import kobo_convert_file
import shutil
import sys, os


def Usage():
    print("""Usage: kobocopy filepath.epub [filepath.epub ...] destdir

Directory structure of input file paths will be duplicated
inside destdir, e.g.
kobocopy Fiction/gatsby.epub SciFi/AndyWeir/artemis.epub /kobo/
will create /kobo/Fiction/gatsby.epub and /kobo/SciFi/AndyWeir/artemis.epub
Any directories will be copied recursively.

You probably want to CD into the root of your books directory
before running this.""")
    sys.exit(1)


def kobocopy_file(inpath, destdir):
    linpath = inpath.lower()
    if not linpath.endswith(".epub"):
        print(inpath, "doesn't end with .epub: skipping!", file=sys.stderr)
        return

    destpath = os.path.normpath(os.path.join(destdir, inpath))
    print("kobocopy_file", inpath, destdir, ": destpath =", destpath)

    destdirpath = os.path.dirname(destpath)
    if not os.path.isdir(destdirpath):
        print("Creating dir", destdirpath)
        os.makedirs(destdirpath)

    if linpath.endswith(".kepub") or linpath.endswith(".kepub.epub"):
        print(inpath, "is already converted! Just copying")
        shutil.copyfile(inpath, destpath)
        return

    print("Calling kobo_convert_file(", inpath, destpath, ")")
    kobopath = kobo_convert_file(inpath, destdirpath)


def kobocopy_file_or_dir(inpath, destdir):
    if os.path.isfile(inpath):
        kobocopy_file(inpath, destdir)
        return

    if not os.path.isdir(inpath):
        print(inpath, "is neither a directory or a file, skipping",
              file=sys.stderr)
        return

    for root, dirs, files in os.walk(inpath):
        for f in files:
            kobocopy_file(os.path.join(root, f), destdir)
        for d in dirs:
            kobocopy_file_or_dir(os.path.join(root, d), destdir)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        Usage()
    destdir = sys.argv[-1]
    if not os.path.isdir(destdir):
        Usage()

    for inpath in sys.argv[1:-1]:
        kobocopy_file_or_dir(inpath, destdir)

