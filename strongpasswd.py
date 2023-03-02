#!/usr/bin/env python3

# Generate a strong random password.
# Websites most often allow a few simple nonalphanumeric characters,
# like .,-, but not the wider set that password managers want to use.
# Firefox's password generator is only alphanumeric:
# https://bugzilla.mozilla.org/show_bug.cgi?id=1559986


import string
import random
import argparse
import sys


ALPHA = string.ascii_lowercase + string.ascii_uppercase
NUM = string.digits
# Websites often allow, and even require, limited punctuation.
PUNCT = '.,-!@?'


def gen_passwd(length, numwords=0, nopunct=False, chars=None, punctchars=None):
    """Generate a random password.
       length:     length in chars
       numwords:   number of words (will be joined with digits or punctuation)
       nopunct:    don't include any punctuation.
       chars:      character set to use
       punctchars: punctuation marks allowed
    """
    if not punctchars:
        punctchars = PUNCT

    passwd = ""

    if numwords:
        wordlist = []
        if nopunct:
            chars = " "
        else:
            chars = NUM + punctchars

        with open("/usr/share/dict/words") as fp:
            for line in fp:
                line = line.strip()
                if "'" in line:
                    continue
                if line[0].isupper():
                    continue
                if len(line) < 5:
                    continue
                wordlist.append(line)

        while numwords:
            if passwd:
                passwd += random.choice(chars)
            passwd += random.choice(wordlist)
            numwords -= 1

        return passwd

    if not chars:
        # Generate a character set.
        # Weight numbers and punctuation higher, to make them more likely
        # to be chosen at least once despite their shorter string length.
        chars = ALPHA + NUM*2 + punctchars*4

    while len(passwd) < length:
        passwd += random.choice(chars)

    return passwd


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a random password")
    parser.add_argument('-l', "--length", default=15, dest="length",
                        type=int, action="store", help="Length")
    parser.add_argument("--np", dest="nopunct", default=False,
                        action="store_true",
                        help="Don't include any punctuation")
    parser.add_argument("--sp", dest="simplepunct", default=False,
                        action="store_true",
                        help="Don't include any punctuation")
    parser.add_argument("-w", "--numwords", dest="numwords", default=0,
                        action="store", type=int,
                        help="Use this many words, joined with num/punct")
    parser.add_argument('-c', "--chars", default='', dest="chars",
                        action="store",
                        help="Character set to use (default %s%s%s)"
                             % (ALPHA, NUM, PUNCT))
    parser.add_argument("--punctchars", default='', dest="punctchars",
                        action="store",
                        help="Punctuation allowed (default %s)" % PUNCT)
    args = parser.parse_args(sys.argv[1:])

    passwd = gen_passwd(args.length, numwords=args.numwords,
                        nopunct=args.nopunct,
                        chars=args.chars, punctchars=args.punctchars)

    print(passwd)
