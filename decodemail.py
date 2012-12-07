#!/usr/bin/env python

# Decode From and Subject lines spammers encode in other charsets
# to try to hide them from spam filters.
# Use in conjunction with programs like procmail or spamassassin,
# instead of something like formail

import sys
import email

# Usage: decodemail headername [inputfile]
# Decode the first line seen that starts with headername (e.g. From:).
# If inputfile is omitted, will use stdin.

header_wanted = sys.argv[1]

if len(sys.argv) > 2 :
    fil = open(sys.argv[2])
else :
    fil = sys.stdin

for line in fil :
    if line.startswith(header_wanted) :
        # print "Original:", line
        for part in email.Header.decode_header(line) :
            sys.stdout.write(part[0])
        print
        sys.exit(0)

print "No such header", header_wanted
sys.exit(1)

