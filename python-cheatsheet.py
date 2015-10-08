#!/usr/bin/env python

# This is a file of reminders of various neat Python features
# that I always forget how to use.

#
# Read a file of name=value pairs and return a dictionary.
#
# https://mail.python.org/pipermail/baypiggies/2015-October/009556.html
def file2dict(filename):
    with open(filename) as af:
        return dict(line.strip().split('=',1) for line in af)

#
# Walk a directory tree
#
def walkfiles(rootdir):
    for root, dirs, files in os.walk(rootdir):
        for f in files:
            print f

#
# map + lambda example
#
def helloall(names):
    return '\n'.join(map(lambda name: "Hello, " + name, names))

#
# filter + lambda example
#
def only_even(numbers):
    return filter(lambda x: x%2 == 0, numbers)

#
# Simple map used for rounding.
# int() truncates, round() rounds but doesn't return an int.
#
def roundall(numbers):
    return map(int, map(round, numbers))

#
# sorting + lambda examples.
#
# The cmp function is obsolete.
# Instead, use a key function,
# which is called on each element of the list prior to sorting.
# https://wiki.python.org/moin/HowTo/Sorting
#
def sort_by_last_letter(words):
    # sorted() returns a new sorted list.
    print sorted(words, key = lambda a: a[-1])

    # list.sort() modifies the list in place
    words.sort(key = lambda a: a[-1])
    print words

#
# Reduce example
#
# https://mail.python.org/pipermail/baypiggies/2015-September/009548.html
# Note: There's also collections.Counter.
def letter_frequency(data):
    def count(total, item):
        total[item] = total.get(item, 0) + 1
        return total
    return reduce(count, data, {})

if __name__ == "__main__":
    import os
    print "This is file:   ", __file__
    print "which is really:", os.path.realpath(__file__)
