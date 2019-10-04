#!/usr/bin/env python3

# Compare two directory trees. Report files that are in one but not
# the other, regardless of where they are in the tree.
# Useful for devices like kobo that don't handle subdirectories well.

import sys, os

def build_index(d):
    '''Build a dictionary of { filename: fullpath }
       of every file under the directory d.
    '''
    index = {}
    for root, dirs, files in os.walk(d):
        for f in files:
            index[f] = os.path.join(root, f)

    return index

if __name__ == '__main__':
    d1 = build_index(sys.argv[1])
    d2 = build_index(sys.argv[2])

    only_in_d1 = []
    only_in_d2 = []

    for f in d1:
        if f not in d2:
            only_in_d1.append(d1[f])

    for f in d2:
        if f not in d1:
            only_in_d2.append(d2[f])

    print("\n ==== Only in", sys.argv[1])
    print('\n'.join(only_in_d1))

    print("\n ==== Only in", sys.argv[2])
    print('\n'.join(only_in_d2))

