#! /usr/bin/env python

# blogtouch
# Copyright 2007 by Akkana Peck: feel free to use this under the GPLv2.

# Walk a static pyblosxom directory tree searching for all files
# containing a regex pattern. For each matching file found,
# set the date on it to be early enough that it will be
# regenerated with ./pyblosxom.cgi --static --incremental

from __future__ import print_function

import sys, os, re


# Extensions to consider:
blog_extensions = [ ".html", ".rss", ".rss20", ".atom" ]

def is_blog_file(filepath):
    for ext in blog_extensions:
        if f.endswith(ext):
            return True

    return False


def fixup_date(filepath):
    # Set the time to ten years earlier:
    tenyears = 315360100
    filestat = os.stat(filepath)
    utimes = ( filestat.st_atime - tenyears, filestat.st_mtime - tenyears )
    os.utime(filepath, utimes)


def check_for_match(patprog, filepath):
    try:
        with open(filepath) as fp:
            for line in fp:
                if (patprog.search(line)):
                    return True

        return False

    except IOError:
        #print("File:", filepath, "missing")
        return False


def check_dir(pat, dirname, names):
    for fil in names:
        if check_for_match(pat, dirname + "/" + fil):
            fixup_date(dirname + "/" + fil)


if len(sys.argv) != 2:
    print("Usage:", sys.argv[0], "pattern")
    sys.exit(0)

print("Setting times to ten years earlier:")
# print("Passing pattern /" + sys.argv[1] + "/")

num_files_changed = 0

pat = re.compile(sys.argv[1])
for root, dirs, files in os.walk(os.path.expanduser("~/web/blog/linux")):
    for f in files:
        filepath = os.path.join(root, f)

        if (is_blog_file(filepath) and check_for_match(pat, filepath)):
            print(filepath)
            num_files_changed += 1
            fixup_date(filepath)

print(num_files_changed, "files updated")
