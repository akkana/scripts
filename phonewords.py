#!/usr/bin/env python3

# Given a phone number like 686-2377,
# print out all the possible English words that could match, like "numbers".
# Inspired by someone who showed up on IRC asking about a homework assignment;
# it sounded like a fun problem so I tried it to see how hard it was.
# (I didn't give the student the solution, though. That would be cheating.)

import sys
import argparse

# Letters corresponding to each number on a phone dialpad:
phoneletters = [ '',
                 '', 'abc', 'def',
                 'ghi', 'jkl', 'mno',
                 'pqrs', 'tuv', 'wxyz' ]

# Use a set for the word list to eliminate dups.
# There are some dups in /usr/share/dict/words,
# where one is capitalized and the other isn't.
Wordlist = set()

WORDLIST = '/usr/share/dict/words'
# WORDLIST = '/tmp/words'

def read_word_list():
    with open(WORDLIST) as fp:
        for line in fp:
            if "'" in line:
                continue
            line = line.strip().lower()
            #     Wordlist.append(line)
            Wordlist.add(line)

    # print("Word list:", Wordlist)

def word2num(word):
    phonenumber = ''
    for letter in word:
        letter = letter.lower()
        for i, letters in enumerate(phoneletters):
            if letter in letters:
                phonenumber += str(i)
    return phonenumber

def find_dups(matchlen):
    '''Find phone numbers that have more than one match, for a given length'''

    lastnum = ''
    lastword = None
    matchwords = None
    for word in Wordlist:
        if len(word) != matchlen:
            continue
        phonenum = word2num(word)
        if phonenum == lastnum:
            if not matchwords:
                matchwords = [ lastword, word ]
            else:
                matchwords.append(word)
        else:
            if matchwords:
                print("%s = %s" % (lastnum, ' '.join(matchwords)))
            matchwords = None

        lastnum = phonenum
        lastword = word

    if matchwords:
        print("%s = %s" % (lastnum, ' '.join(matchwords)))

def find_words(phonenum, single_word=True):
    '''Takes either a string of digits, or a list of numbers.
       If single_word is true, only allow a single word of the same length
    '''

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
        # If we're only matching a single word, lengths must be the same:
        if single_word and len(word) != numlen:
            continue
        # Even if we're matching multiple words, the word length can't
        # be greater than the number length:
        if len(word) > numlen:
            continue
        # print("Checking", word)

        matches = True
        for i, digit in enumerate(digits):
            # print("digit", digit, "phoneletters[digit]", phoneletters[digit],
            #       "word[i]", word[i])
            if word[i] not in phoneletters[digit]:
                matches = False
                break
        if matches:
            matchwords.append(word)

    return matchwords

if __name__ == '__main__':
    read_word_list()

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', action="store", dest="number",
                        help='Phone number to map to words')
    parser.add_argument('-w', action="store", dest="word",
                        help='Word to map to a phone number')
    parser.add_argument('-d', action="store", dest="find_dups", type=int,
                        help='Find duplicates for a given number of digits')
    args = parser.parse_args(sys.argv[1:])

    if args.find_dups:
        find_dups(args.find_dups)

    if args.word:
        print(word2num(args.word))

    if args.number:
        print(' '.join(find_words(args.number)))


