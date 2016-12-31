#!/usr/bin/env python

# This is a file of reminders of various neat Python features
# that I always forget how to use.

# Split a long string over multiple lines in the source file
url1 = ( "http://www.crummy.com/software/BeautifulSoup/"
         "bs3/documentation.html" )
# Note no commas in the parenthesized one:
# parentheses without a comma inside are just grouping, not a tuple.
(42)    # is type int
(42,)   # is a tuple with len 1

# You can also use a backslash and no parentheses:
url2 = "http://www.crummy.com/software/BeautifulSoup/" \
       "bs3/documentation.html"

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
# Parse a date in RFC 2822 format.
#
# email.utils.parsedate returns a tuple.
t = time.mktime(email.utils.parsedate("Thu, 11 Aug 2016 14:46:50 GMT")))
(y, m, d, h, m, s, weekday, yearday, isdst) = t
# the last three items of the tuple aren't very useful: typically 0, 1, -1.
# -1 means "unknown" for the dst flag.
secs_since_epoch = time.mktime(t)

t2 = time.mktime_tz(email.utils.parsedate("Thu, 11 Aug 2016 14:46:50 GMT")))
(y, m, d, h, m, s, weekday, yearday, isdst, offset_from_utc) = t2
secs_since_epoch = email.utils.mktime_tz(t2)

#
# Parse a date in unknown format into a datetime.datetime object
#
import dateutil.parser
d = dateutil.parser.parse("2012-08-16 14:25:05.265739")
d = dateutil.parser.parse("10/31/2016 14:25")
d = dateutil.parser.parse("6/15/2016 14:25 MDT")

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
# Fuzzy string match.
# SequenceMatcher's first argument is a function that returns true for
# characters considered to be "junk". For instance, if blanks are junk,
# lambda x: x == " "
# To consider nothing as junk, pass None.
#
from difflib import SequenceMatcher

best_ratio = -1
best_match = None
for b in string_list:
    r = SequenceMatcher(None, matchname, b).ratio()
    if r > best_ratio:
        best_match = b
        best_ratio = r

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

#
# Enum values in PyGTK. I'm forever running up against dialogs that
# return some random undocumented negative number from run(),
# and there's no way to find out which gtk.RESPONSE_FOO
# the negative number corresponds to.
#
def enumval(e):
    for i in range(-1000, 1000):
        if e == i:
            return i
    return None

# This is also a useful hint for how to look up an arbitrary string
# in the environment.
# list from http://www.pygtk.org/pygtk2reference/gtk-constants.html#gtk-response-type-constants
for s in ("NONE", "REJECT", "ACCEPT", "DELETE_EVENT", "OK", "CANCEL", "CLOSE", "YES", "NO", "APPLY", "HELP"):
    print s, eval("enumval(gtk.RESPONSE_" + s + ")")
# As of Dec 2016, this gives:
# NONE -1
# REJECT -2
# ACCEPT -3
# DELETE_EVENT -4
# OK -5
# CANCEL -6
# CLOSE -7
# YES -8
# NO -9
# APPLY -10
# HELP -11


