#!/usr/bin/env python

# This is a file of reminders of various neat Python features
# that I always forget how to use.

# On #python as of early 2017, recommended beginning Python books include
# http://greenteapress.com/wp/think-python-2e/
# https://automatetheboringstuff.com/
# (the oft-recommended "Learn Python the Hard Way" is not well favored).
# I can't vouch for these books myself.

########################################################
# What's available in objects and modules?
########################################################

# Show methods in an object
dir(obj)

# Does a function exist in a module?
hasattr(os, 'get_terminal_size'):
# You can also get with a default:
getattr(os, 'get_terminal_size', "Doesn't exist")

# Is something a particular type? (But of course duck-typing is better.)
if type(s) is str:
    print("It's a string")

# More deprecated:
if type(s) == types.StringType:
    print "It's a string"

# Is something list-like?
if hasattr(l, "__getitem__"):
    print "It's list-like"
else:
    print "It's more scalar-like"
# Be cautious with this, though: strings are list-like,
# and even if you iterate over them you never get down to a scalar char,
# just unit-length strings.

# Remove items from a list: I always forget how to do this.
mylist.remove("item")    # Removes the first instance of "item"
mylist.pop(i)            # Removes and returns list[i]

########################################################
# Debugging and stack traces
########################################################

# Print a stack trace -- how did we get here?
traceback.print_stack()

# Equivalent of verbose mode in a shell: print each line before executing.
python -m trace --trace /tmp/foo.py

########################################################
# Stringy stuff
########################################################

# Decode vs. Encode:
# "string of bytes".decode('utf-8')  --> unicode
# u"unicode string".encode('utf-8')  --> bytes
# Either of these can take
#   errors='replace', 'ignore', 'backslashreplace', 'xmlcharrefreplace'
>>> u = u'piñon'
>>> u
u'pi\xf1on'
# For Python3 skip to the end of this file.

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

# raw string literals: r'' avoids any backslash escapes.
# printf-style %x still works, e.g. r'abc %d' % 42
r = r'abc\def'
c = 'abc\\def'
r == c    # True

########################################################
# iterator, list and dictionary helpers
########################################################

# Pairwise loops with zip():
names = ["Eiffel Tower", "Empire State", "Sears Tower"]
heights = [324, 381, 442]
for name, height in zip(names, heights):
    print "%s: %s meters" % (name, height)

# Or make a dictionary from a zip():
tall_buildings = dict(zip(names, heights))
print max(tall_buildings.values())

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
            print os.path.join(root, f)

# os.walk is handy, but it doesn't allow any type of sorting.
# So here's a rewritten os.walk that sorts alphabetically.
def pathwalk(top, topdown=True, onerror=None, followlinks=False, sortfn=None):
    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.path.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.
    try:
        names = os.listdir(top)
        if sortfn:
            names.sort(sortfn)
        else:
            names.sort()
    except os.error, err:
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    for name in names:
        if os.path.isdir(os.path.join(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        path = os.path.join(top, name)
        if followlinks or not os.path.islink(path):
            for x in pathwalk(path, topdown, onerror, followlinks):
                yield x
    if not topdown:
        yield top, dirs, nondirs

########################################################
# Argument parsing
########################################################
#python recommends click first, then argparse, over optparse.

########################################################
# Dates and times
########################################################

#
# Add N months to a date: same day of month but next month.
#
import datetime
from dateutil.relativedelta import relativedelta
today = datetime.date.today()
three_months_from_now = today + relativedelta(months=3)
# Note that relativedelta can also take a month= as well as a months=.
# month gives you the current dayofmonth in a specific month number;
# months gives you how many months relative to the current one.
# For differences of just days or weeks, datetime.timedelta works.

# Subtracting datetimes gives a datetime.timedelta, and that's also
# a good way to add or subtract time from a datetime.
now = datetime.datetime.now()
if (now - self.end).seconds < 7200:
    self.end = now - datetime.timedelta(seconds=7200)

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
# Also see the Arrow library, a Datetime replacement
# that offers super-general date parsing like "an hour ago".

#
# Another of parsing using calendar but not dateutils:
#
import datetime
import calendar
today = datetime.date.today()
days_this_month = calendar.monthrange(today.year, today.month)[1]
one_month_from_now = today + datetime.timedelta(days=days_this_month)

# There's also isodate.parse_datetime which I haven't looked into yet.

########################################################
# OS-specific stuff
########################################################

# Read keys in cbreak mode.
# Some info at:
# http://docs.python.org/2/faq/library.html#how-do-i-get-a-single-keypress-at-a-time
# but it's incomplete, so see keyreader.py for a better solution.
#
# Of course, you can also do this with curses.

########################################################
# Lambda foo
########################################################

#
# map + lambda example
#
def helloall(names):
    return '\n'.join(map(lambda name: "Hello, " + name, names))
# but in practice, you generally shouldn't need map+lambda, because
# map(lambda x: <expr>, xs) can be rewritten as (<expr> for x in xs)
# and the latter is much more readable.

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

######################################################
# Decorators -- attempt at a useful example.
######################################################

#
# Timer decorator without arguments:
#
import time

def timing_function(fn):
    """
    Returns the time a function takes to execute.
    """
    def wrapper():
        t1 = time.time()
        fn()
        t2 = time.time()
        return "It took: %s" % str(t2 - t1)
    return wrapper

@timing_function
def sumit():
    bignum = 100000
    tot = 0
    for num in (range(0, bignum)):
        tot += num
    print("Sum (0-%d) = %d" % (bignum, tot))

output = sumit()
print("output = '%s'" % str(output))

#
# But adding an argument is counterintuitive.
# If you give sumit an argument, sumit(bignum),
# that's taken as being an argument for wrapper(), not for fn().
# If you want sumit() to take an argument, you have to do it this way:
#
def timing_function(fn):
    """
    Returns the time a function takes to execute.
    """
    def wrapper(outer_arg):  # outer_arg is the arg passed to sumit
        def wrapped(*args):
            t1 = time.time()
            fn(outer_arg)
            t2 = time.time()
            return "%d: It took: %s" % (outer_arg, str(t2 - t1))
        return wrapped(fn)  # This is what gets returned when you call sumit(x)
    return wrapper

@timing_function
def sumit(bignum):
    tot = 0
    for num in (range(0, bignum)):
        tot += num
    print("Sum (0-%d) = %d" % (bignum, tot))

output = sumit(100000)
print("output = '%s'" % str(output))

#
# What if you want the decorator to also take arguments?
#
def repeat_timing_function(numreps):
    def wrap(fn):
        def wrapped_f(*args):
            # args are the args to the outside function (=bignum)
            # arg1, arg2, arg3 are the decorator arguments (=numreps)
            t1 = time.time()
            for i in range(numreps):
                fn(*args)
            t2 = time.time()
            return "%d: It took: %s" % (args[0], str(t2 - t1))
        return wrapped_f
    return wrap

@repeat_timing_function(5)
def summit(bignum):
    tot = 0
    for num in (range(0, bignum)):
        tot += num
    print("Sum (0-%d) = %d" % (bignum, tot))

output = summit(100000)
print("output = '%s'" % str(output))


################################################################
# Matplotlib tips
################################################################

self.ax1 = self.fig.add_subplot(2, 1, 1)   # nrows, ncols, plotnum

# Trimming all the spurious whitespace:

# Trim whitespace within each plot:
ax.set_xlim([0, enddate])
ax.set_ylim([0, data[-1]])

# Trim whitespace between plots:
# pad controls padding around the top, bottom and sides of the page;
# w_pad controls space between plots horizontally (if columns > 1),
# h_pad controls space between plots vertically (if rows > 1).
plt.tight_layout(pad=2.0, w_pad=10.0, h_pad=3.0)

# There are lots and lots of other things that are supposed to
# eliminate whitespace; most of them don't work, and some of them,
# like ax.axis('tight') or plt.axis('tight'), prevent set_?lib
# and tight_layout from working.

# Exit on key q
plt.figure(1).canvas.mpl_connect('key_press_event',
                                 lambda e:
                                     sys.exit(0) if e.key == 'ctrl+q'
                                     else None)


################################################################
# Python3 differences
################################################################

# Migrate python2 to python3 in place (omit -n to leave a .bak):
$ 2to3 -wn file_or_directory

# All strings in python3 are automatically unicode,
# and you can just pass encoding as a second argument when you
# coerce between str and byte, no need to remember encode/decode.

# Encode/decode in PYTHON3:
>>> str(b'string of bytes')
'string of bytes'
>>> str(b'string of bytes', 'utf-8')
'string of bytes'
>>> bytes('piñon', 'utf-8')
b'pi\xc3\xb1on'
>>> str(b'pi\xc3\xb1on')
"b'pi\\xc3\\xb1on'"
>>> str(b'pi\xc3\xb1on', 'utf-8')
'piñon'
