#!/usr/bin/env python

# Photo Search:
# Search under the current dir, or the first argument given,
# for grep matches within files named "Keywords".
# Then translate that to a list of full pathnames.
# Copyright 2007,2009,2020 by Akkana Peck: share and enjoy under the GPLv2 or later.

# Wish list: Boolean logic. Currently this can search only for one
# term/phrase at a time.

from __future__ import print_function

import glob
import re
import sys, os


def search_for_keywords(grepdirs, orpats, andpats, notpats,
                        ignorecase):
    """Inside grepdirs, open files named Tags or Keywords.
       Search those lines looking for matches in the keywords for pats.
       Each item in grepdirs may be a shell-style pattery, like 20??
       (the style used by python's glob module):
       first we'll try to match the item exactly, then if not,
       try to match it as a pattern.
       ~ is allowed.
    """
    results = []

    if ignorecase:
        orpats = [ p.lower() for p in orpats ]
        andpats = [ p.lower() for p in andpats ]
        notpats = [ p.lower() for p in notpats ]

    for pat in grepdirs:
        for d in glob.glob(os.path.expanduser(pat)):
            for root, dirs, files in os.walk(d):
                if not files:
                    continue
                for f in files:
                    if f == "Tags" or f == "Keywords":
                        results += search_for_keywords_in(root, f,
                                                          orpats,
                                                          andpats,
                                                          notpats,
                                                          ignorecase)
                        break   # XXX would prefer to break out of root, not f
    return results


def search_for_keywords_in(d, f, orpats, andpats, notpats, ignorecase):
    """Search in d (directory)/f (file) for lines matching or,
       and and not pats. f is a file named Tags or Keywords,
       and contains lines in a format like:
       [tag ]keyword, keyword: file.jpg file.jpg
       Also treat the directory name as a tag:
       return True if the patterns match the directory name.
       Return a list of files.
    """
    results = []
    filetags = {}
    if d.startswith('./'):
        d = d[2:]
    with open(os.path.join(d, f)) as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            if line.startswith("tag "):
                line = line[4:]
            elif line.startswith("category "):
                continue
            # Now we know it's a tag line.
            parts = line.split(':')
            if len(parts) < 2:
                continue
            tags = parts[0].strip()
            # There may be several comma-separated tags here, but we
            # actually don't care about that for matching purposes.

            for imgfile in parts[1].strip().split():
                filepath = os.path.join(d, imgfile)
                if not os.path.exists(filepath):
                    continue    # Don't match files that no longer exist
                if filepath not in list(filetags.keys()):
                    filetags[filepath] = tags
                else:
                    filetags[filepath] += ', ' + tags

                # Add the name of the directory as a tag.
                # Might want to make this optional at some point:
                # let's see how well it works in practice.
                if d not in filetags[filepath]:
                    filetags[filepath] += ", " + d

    # Now we have a list of tagged files in the directory, and their tags.
    for imgfile in list(filetags.keys()):
        tags = filetags[imgfile]

        if has_match(tags, orpats, andpats, notpats, ignorecase):
            results.append(imgfile)

    return results


def has_match(tags, orpats, andpats, notpats, ignorecase):
    """Do the tags contain any of the patterns in orpats,
       AND all of the patterns in andpats,
       AND none of the patterns in notpats?'
       tags is a string representing all the tags on one file;
       the *pats are lists.
    """
    #print "Looking for OR", orpats, "AND", andpats, "NOT", notpats, "IN", tags
    if ignorecase:
        flags = re.IGNORECASE
    else:
        flags = 0
    for pat in notpats:
        if pat in tags:
            return False
    for pat in andpats:
        if pat not in tags:
            return False
    if not orpats:
        return True
    for pat in orpats:
        if re.search(pat, tags, flags):
        #if pat in tags:
            return True
    return False

def Usage():
    print('''Usage: %s [-s] [-d dirs] condition [condition ...]

Search for files matching patterns in Tags or Keywords files.
Will search recursively under the current directory unless -d is specified.

Conditions can include three types of patterns:
  1. Starts with +: must be present (AND).
  2. Starts with -: must NOT be present (NOT).
  3. Starts with neither: one of these must be present (OR).

Optional arguments:
  +i              don't ignore case (case is ignored by default)
  -d dir,dir,dir  comma-separated list of directories to use (else .)
                  Each dir may be a shell-style pattern, e.g. 19??,20??

Copyright 1009,2014,2020 by Akkana Peck.
Share and enjoy under the GPL v2 or later.''' % os.path.basename(sys.argv[0]))
    sys.exit(0)


def parse_args(args):
    ret = {}

    if not len(args) or args[0] == '-h' or args[0] == '--help':
        Usage()

    # Loop over flag args, which must come before pattern args.
    while True:
        if args[0] == '-i':
            ret["ignorecase"] = True
            args = args[1:]
        elif args[0] == '+i':
            ret["ignorecase"] = False
            args = args[1:]
        elif args[0] == '-d':
            if len(args) == 1:
                Usage()
            ret["dirlist"] = args[1].split(',')
            args = args[2:]
        else:
            break

    if "dirlist" not in ret:
        ret["dirlist"] = ['.']
    if "ignorecase" not in ret:
        ret["ignorecase"] = True

    ret["andpats"] = []
    ret["orpats"]  = []
    ret["notpats"] = []
    for pat in args:
        if pat[0] == '+':
            ret["andpats"].append(pat[1:])
        elif pat[0] == '-':
            ret["notpats"].append(pat[1:])
        else:
            ret["orpats"].append(pat)

    return ret


if __name__ == "__main__":
    # Sadly, we can't use argparse if we want to be able to use -term
    # to indicate "don't search for that term".

    args = parse_args(sys.argv[1:])

    r = search_for_keywords(args["dirlist"],
                            args["orpats"], args["andpats"], args["notpats"],
                            args["ignorecase"])
    s = set(r)
    r = list(s)
    r.sort()
    for f in r:
        print(f, end=' ')
    print()


