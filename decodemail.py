#!/usr/bin/env python3

# Decode From and Subject lines spammers encode in other charsets
# to try to hide them from spam filters. (RFC 2047 encoding.)
# Use in conjunction with programs like procmail or spamassassin,
# instead of something like formail.

from __future__ import print_function

import sys, os
import email
import email.utils

from email.header import Header, decode_header

# https://pythonhosted.org/kitchen/unicode-frustrations.html
# says this should help the codec problem,
# but that's for python2. In python3 it just prints:
#   TypeError: write() argument must be str, not bytes
# import codecs
# UTF8Writer = codecs.getwriter('utf8')
# sys.stdout = UTF8Writer(sys.stdout)

Debug = False

progname = os.path.basename(sys.argv[0])
Usage = """Usage: %s [-a] headername [filename]

Find a line matching the given header name (Subject:, From:, etc.)
and decode it according to RFC 2047.
Without a filename, will read standard input.
Adding -a will print all matches within the given file, not just the first.
Multiple headers may be combined with |

Example: %s -a Subject: /var/mail/yourname
         %s -a 'Subject:|To:|From:' folder folder""" % (progname, progname,
                                                        progname)

def decode_piece(piece):
    ret = ''

    # In Python 2 this was easy: just loop over decode_header(piece).
    # In Python 3 it's trickier, because decode_header randomly
    # may return str or bytes in part[0], and although the documentation
    # suggests that part[1], the charset, should be set for decoded strings
    # and unset for bytes, in practice part[1] doesn't tell you
    # anything about whether part[0] is str or bytes.
    # So you have to check the type.
    for part in decode_header(piece):
        if type(part[0]) is bytes:
            ret += part[0].decode(errors='replace')
        else:
            ret += part[0]

        # Special case: the header itself comes out with charset None
        # and decode doesn't add a space between it and the next part,
        # even though there was a space in the original. So add one
        # (it's better to have too many spaces than too few).
        # I'm taking a wild guess that the relevant factor here is
        # the None charset rather than the fact that it matched
        # the header, but keep an eye open for counterexamples.
        if not part[1]:
            ret += ' '

    return ret

def decode_and_split(piece, header_wanted):
    thispiece = decode_piece(piece)

    # If the header is an address, we have to split it into parts
    # before we can decode it. If it's another header
    # such as Subject, we can't do that.
    if header_wanted.startswith("From") \
            or header_wanted.startswith("To") \
            or header_wanted.startswith("Cc") \
            or header_wanted.startswith("Bcc"):
        pieces = email.utils.parseaddr(thispiece)
        if pieces[0] or pieces[1]:
            if Debug:
                print("formataddr says: '%s'" % \
                      email.utils.formataddr(map(decode_piece, pieces)).strip())
            return header_wanted + ' ' + \
                email.utils.formataddr(map(decode_piece,
                                           pieces)).strip()
        else:
            print("parseaddr failed on", thispiece, file=sys.stderr)

    return thispiece

def decode_file(filename, header_wanted, all=False, casematch=False):
    if filename == '-':
        fil = sys.stdin
    else:
        fil = open(filename, encoding="utf-8", errors='replace')

    if not casematch:
        header_wanted = header_wanted.lower()

    # header_wanted can be multiple headers, e.g. From:|To:
    # so split them.
    headers = header_wanted.split('|')

    output = ''
    found_something = False
    for line in fil:
        if not casematch:
            testline = line.lower()

        if Debug:
            # Were there any bad characters added from errors='replace'?
            # Python replaces them with U+FFFD, REPLACEMENT CHARACTER
            if '\ufffd' in line:
                print("REPLACEMENT CHAR!", end='')
            print("line:", line, end='')

        # Are we looking for continuation lines?
        if output:
            if testline.startswith(' ') or testline.startswith('\t'):
                # It's a continuation line: keep appending.
                output += decode_piece(line.strip())
                # XXX should probably remember the header we're currently
                # matching, and decode_and_split with that header.
                continue

            # It's not a continuation line. Print output, and either
            # exit, or clear output and go back to looking for headers.
            try:
                # print(output.encode('utf-8', "surrogatepass"))
                # print(type(output), file=sys.stderr)
                print(output)
            except UnicodeEncodeError as e:
                # output is ultimately whatever type that comes from
                # email.header.decode_header, and printing it can
                # raise a UnicodeEncodeError because python is so insistent
                # on using ascii codec despite locale being en_US.UTF-8.
                print("Type causing exception was", type(output),
                      file=sys.stderr)
                raise(e)
            if all:
                output = ''
            else:
                sys.exit(0)

        # If it matches the header we seek, or if we've already started
        # matching the header and we're looking for continuation lines,
        # build up our string:
        for header_wanted in headers:
            # if Debug:
            #     print("=== looking for", header_wanted)

            if testline.startswith(header_wanted):
                found_something = True
                if Debug:
                    print("\nFound something:", line)
                output = decode_and_split(line.strip(), header_wanted)
                break    # No need to look for other headers on this line

    if output:
        if Debug:
            print("final output:", end='')
        print(output.strip())

    # If we get here, we never matched a header,
    # or ended with a continuation line.
    if not found_something:
        print("No such header", header_wanted, "in", filename)
        return

all = False

if len(sys.argv) > 2:
    if sys.argv[1] == '-h' or sys.argv[1] == '--help':
        print(Usage)
        sys.exit(1)

    # A -a argument means don't stop at the first header,
    # decode all matching headers in the file.
    if sys.argv[1] == '-a':
        all = True
        sys.argv = sys.argv[1:]

if len(sys.argv) <= 1:
    print(Usage)
    sys.exit(1)

header_wanted = sys.argv[1]

try:
    if len(sys.argv) > 2:
        for filename in sys.argv[2:]:
            decode_file(filename, header_wanted, all)
    else:
        fil = sys.stdin
        decode_file('-', header_wanted)
except KeyboardInterrupt:
    sys.exit(1)

