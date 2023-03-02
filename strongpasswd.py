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


def gen_passwd(length, nopunct=False, chars=None, punctchars=None):
    if not punctchars:
        punctchars = PUNCT
    if not chars:
        # Generate a character set.
        # Weight numbers and punctuation higher, to make them more likely
        # to be chosen at least once despite their shorter string length.
        chars = ALPHA + NUM*2 + punctchars*4

    passwd = ""
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
    parser.add_argument('-c', "--chars", default='', dest="chars",
                        action="store",
                        help="Character set to use (default %s%s%s)"
                             % (ALPHA, NUM, PUNCT))
    parser.add_argument("--punctchars", default='', dest="punctchars",
                        action="store",
                        help="Punctuation allowed (default %s)" % PUNCT)
    args = parser.parse_args(sys.argv[1:])

    passwd = gen_passwd(args.length, args.nopunct,
                        chars=args.chars, punctchars=args.punctchars)

    print(passwd)
