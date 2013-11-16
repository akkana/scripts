#!//usr/bin/env python

# Count syllables in a word.
#
# Doesn't use any fancy knowledge, just a few super simple rules:
# a vowel starts each syllable;
# a doubled vowel doesn't add an extra syllable;
# two or more different vowels together are a diphthong,
# and probably don't start a new syllable but might;
# y is considered a vowel when it follows a consonant.
#
# Even with these simple rules, it gets results far better
# than python-hyphenate with the libreoffice hyphenation dictionary.
#
# Copyright 2013 by Akkana Peck http://shallowsky.com.
# Share and enjoy under the terms of the GPLv2 or later.

import sys

verbose = False

def count_syllables(word):
    vowels = ['a', 'e', 'i', 'o', 'u']

    on_vowel = False
    in_diphthong = False
    minsyl = 0
    maxsyl = 0
    lastchar = None

    word = word.lower()
    for c in word:
        is_vowel = c in vowels

        if on_vowel == None:
            on_vowel = is_vowel

        # y is a special case
        if c == 'y':
            is_vowel = not on_vowel

        if is_vowel:
            if verbose: print c, "is a vowel"
            if not on_vowel:
                # We weren't on a vowel before.
                # Seeing a new vowel bumps the syllable count.
                if verbose: print "new syllable"
                minsyl += 1
                maxsyl += 1
            elif on_vowel and not in_diphthong and c != lastchar:
                # We were already in a vowel.
                # Don't increment anything except the max count,
                # and only do that once per diphthong.
                if verbose: print c, "is a diphthong"
                in_diphthong = True
                maxsyl += 1
        elif verbose: print "[consonant]"

        on_vowel = is_vowel
        lastchar = c

    # Some special cases:
    if word[-1] == 'e':
        minsyl -= 1
    # if it ended with a consonant followed by y, count that as a syllable.
    if word[-1] == 'y' and not on_vowel:
        maxsyl += 1

    return minsyl, maxsyl

if __name__ == '__main__':
    if sys.argv[1].startswith('-f'):
        for word in open(sys.argv[2]):
            word = word.strip()
            smax, smin = count_syllables(word)
            print word, smax, smin
    else:
        for word in sys.argv[1:]:
            word = word.strip()
            smax, smin = count_syllables(word)
            print word, smax, smin
