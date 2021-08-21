#!/usr/bin/env python3

import unicodedata
import sys
import re
import argparse


# maximum valid code point
MAXUNI = 0x10FFFF


def decode_char(c):
    print("%2c  U+%-7X %s" % (c, ord(c), unicodedata.name(c)))


def unisearch(patlist):
    for i in range(33, MAXUNI):
        c = chr(i)

        try:
            name = unicodedata.name(c)
        except ValueError:
            # print("char", i, "has no name")
            continue

        matched = True
        for pat in patlist:
            if not re.search(pat, name, flags=re.IGNORECASE):
                matched = False
                break
        if matched:
            print("%2c  U+%-7X %s" % (c, i, unicodedata.name(c)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Decode or find unicode chars")
    parser.add_argument('-d', "--decode", dest="decode", default=True,
                        action="store_true",
                        help="(default) Print unicode codepoints and names"
                             " of given chars")
    parser.add_argument('-s', "--search", dest="search", default=False,
                        action="store_true",
                        help="Match patterns (regex) in unicode names")
    args, rest = parser.parse_known_args(sys.argv[1:])

    if args.search:
        unisearch(rest)

    else:
        for w in rest:
            for c in w:
                decode_char(c)



