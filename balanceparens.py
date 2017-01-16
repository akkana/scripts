#!/usr/bin/env python

import sys

def check_balance(filename):
    parenlevel = 0
    bracketlevel = 0
    bracelevel = 0
    for line in open(filename).read():
        for c in line:
            if c == '(':
                parenlevel += 1
            elif c == ')':
                parenlevel -= 1
            elif c == '[':
                bracketlevel += 1
            elif c == ']':
                bracketlevel -= 1
            elif c == '{':
                bracelevel += 1
            elif c == '}':
                bracelevel -= 1

    print(filename + ":")
    print("  parenlevel: %d" % parenlevel)
    print("  bracketlevel: %d" % bracketlevel)
    print("  bracelevel:%d " % bracelevel)

if __name__ == '__main__':
    for f in sys.argv[1:]:
        check_balance(f)
