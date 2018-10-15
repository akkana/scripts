#!/usr/bin/env python3

# Given a phone number like 686-2377,
# print out all the possible English words that could match, like "numbers".
# Inspired by someone who showed up on IRC asking about a homework assignment;
# it sounded like a fun problem so I tried it to see how hard it was.
# (I didn't give the student the solution, though. That would be cheating.)

import sys
import argparse
import collections

# Letters corresponding to each number on a phone dialpad:
phoneletters = [ '',
                 '', 'abc', 'def',
                 'ghi', 'jkl', 'mno',
                 'pqrs', 'tuv', 'wxyz' ]

# Use a set for the word list to eliminate dups.
# There are some dups in /usr/share/dict/words,
# where one is capitalized and the other isn't.
# set is also massively faster than using a list or an OrderedDict.
# However, it's unordered.
Wordlist = set()

WORDLIST = '/usr/share/dict/words'
# WORDLIST = '/tmp/words'

def read_word_list():
    with open(WORDLIST) as fp:
        for line in fp:
            if "'" in line:
                continue
            line = line.strip()
            Wordlist.add(line)

    # print("Word list:", Wordlist)

def word2num(word):
    phonenumber = ''
    for letter in word:
        letter = letter.lower()
        digit = None
        for i, letters in enumerate(phoneletters):
            if letter in letters:
                digit = i
                break
        if not digit:
            raise RuntimeError("Can't map word " + word)
        phonenumber += str(i)
    return phonenumber

def find_words(phonenum, multi_wordlen=3):
    '''Takes either a string of digits, or a list of numbers.
       If single_word is true, only allow a single word of the same length
    '''

    # print("find_words(", phonenum)

    digits = []
    matchwords = []

    # Translate them all to ints
    for digit in phonenum:
        try:
            digits.append(int(digit))
        except:
            print(digit, "isn't an int, skipping")
    # print("digits", digits)

    numlen = len(digits)

    for word in Wordlist:
        wordlen = len(word)

        # If we're only matching a single word, lengths must be the same:
        if not multi_wordlen and wordlen != numlen:
            continue
        # Even if we're matching multiple words, the word length can't
        # be greater than the number length:
        if wordlen > numlen:
            continue
        # print("Checking", word)

        matches = True
        for i, digit in enumerate(digits):
            # Are we at the end of the current word, and should now try
            # matching other words?
            if wordlen == i:
                if multi_wordlen and \
                   wordlen > multi_wordlen and \
                   numlen - wordlen >= multi_wordlen:
                    extra_words = find_words(digits[i:], multi_wordlen)
                    for xw in extra_words:
                        matchwords.append(word + ' ' + xw)
                # Whether or not we looked to add additional words,
                # we're done matching this word, it isn't long enough
                # by itself.
                matches = False
                break

            # print("digit", digit, "phoneletters[digit]", phoneletters[digit],
            #       "word[i]", word[i])
            if word[i] not in phoneletters[digit]:
                matches = False
                break

        if matches:
            matchwords.append(word)

    return matchwords

def find_dups(matchlen):
    '''Find phone numbers that have more than one match, for a given length.
       Returns an OrderedDict where the keys are number of matches,
       and the values are OrderedDicts whose keys are all the phone
       numbers that have that many matches (values are the match words).
    '''

    print("Looking for duplicates of length %d ..." % matchlen)

    curmatches = []
    allmatches = collections.OrderedDict()
    # Looping over the Wordlist set is very fast.
    # Looping over sorted(Wordlist) is much much slower.
    # So instead, loop over the set and sort the results later.
    # Unfortuntately, that means we can't print results as they're found,
    # only after everything is found.
    for word in Wordlist:
        if len(word) != matchlen:
            continue

        if word in curmatches:
            continue

        # print(word)
        try:
            phonenum = word2num(word)
        except RuntimeError:
            # Words that include characters not on a phone pad,
            # like croûton or naiveté:
            print("Can't map", word)
            continue
        curmatches = find_words(phonenum, multi_wordlen=0)
        num_matches = len(curmatches)
        if num_matches > 1:
            # print(phonenum, curmatches)
            if num_matches not in allmatches:
                allmatches[num_matches] = collections.OrderedDict()
            allmatches[num_matches][phonenum] = curmatches

    return allmatches

if __name__ == '__main__':
    read_word_list()

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', action="store", dest="number",
                        help='Phone number to map to words')
    parser.add_argument('-w', action="store", dest="word",
                        help='Word to map to a phone number')
    parser.add_argument('-d', action="store", dest="find_dups", type=int,
                        help='Find duplicates for a given number of digits')
    parser.add_argument('-m', action="store", dest="multi",
                        type=int, default=3,
                        help='Allow strings of multiple words of this length or greater (default 3). Use -m0 to disallow multiples.')
    args = parser.parse_args(sys.argv[1:])

    if args.find_dups:
        dups = find_dups(args.find_dups)
        # print("Got", dups)
        for num_matches in sorted(dups):
            for number in sorted(dups[num_matches]):
                print("%s: %s" % (number, ' '.join(dups[num_matches][number])))

    if args.word:
        print(word2num(args.word))

    if args.number:
        print('\n'.join(find_words(args.number, multi_wordlen=args.multi)))


