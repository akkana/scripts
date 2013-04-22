#!/usr/bin/env python

# find filenames in dir1 that are NOT in dir2.
# It need not be in the same place -- this is useful instead of diff -r
# when you've reordered a file tree.

import sys, os

# Get the set of files in dir1:
files1 = set()
for root, dirs, files in os.walk(sys.argv[1]) :
    for f in files :
        files1.add(f)

# Get the set of files in dir2:
files2 = set()
for root, dirs, files in os.walk(sys.argv[2]) :
    for f in files :
        files2.add(f)

print "In", sys.argv[1], "but not", sys.argv[2], ":"
print '\n'.join(files1 - files2)
print
print "In", sys.argv[2], "but not", sys.argv[1], ":"
print '\n'.join(files2 - files1)
