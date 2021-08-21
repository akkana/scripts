#!/usr/bin/env python3

import unicodedata
import sys

def decode_char(c):
    print("%2c  U+%-7X %s" % (c, ord(c), unicodedata.name(c)))

if __name__ == '__main__':
    for w in sys.argv[1:]:
        for c in w:
            decode_char(c)



