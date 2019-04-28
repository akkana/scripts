#!/usr/bin/env python

# This is a file of reminders of various neat Python features
# that I always forget how to use.

# On #python as of early 2017, recommended beginning Python books include
# http://greenteapress.com/wp/think-python-2e/
# https://automatetheboringstuff.com/
# (the oft-recommended "Learn Python the Hard Way" is not well favored).
# I can't vouch for these books myself.

########################################################
# Interactive Python interpreter
########################################################
# Reload a module you already imported: modulename isn't quoted.
import modulename
reload(modulename)
# If you've imported it under some other name, use the name you used
import modulename as mn
reload(mn)

#############################################################
# What's available in objects and modules? and type-checking.
#############################################################

# Show methods in an object
dir(obj)
# Does a function exist in an object?
if hasattr(obj, 'attr_name'):
if 'attr_name' in dir(obj):

# Does a function exist in a module?
hasattr(os, 'get_terminal_size'):
# You can also get with a default:
getattr(os, 'get_terminal_size', "Doesn't exist")

# Is a variable defined? You have to check locals and globals separately.
if 'myVar' in locals():
if 'myVar' in globals():

# Or, more generally,
try:
    myVar
except NameError:
    myVar = None

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
# Be cautious with this, though: strings are list-like.

# Is something a dict? Use isinstance rather than type()
# because isinstance will work for derived classes.
if isinstance(x, dict)

# Difference between is and ==:
# is checked whether two things are the same object (reference equality),
# == only tests for value equality.
#
# The place where this is most important is nan: (nan == nan) -> False
# but (nan is nan) -> True.
# However, in lists or tuples this breaks, [nan] == [nan] -> True
# You can also use math.isnan(x)
#
# Testing thing is None rather than thing == None is idiomatic;
# testing thing == None supposedly allows a few non-None objects
# to masquerade as None, but I haven't been able to find an example.
# Of course, don't use "is" for lists, strings or other complex types,
# or even for integers; it may work for small integers because python
# caches them, but not for larger ones.

# Update an object from a dictionary, obj.something = d['something']
for k in d:
    setattr(obj, k, d[k])

########################################################
# One-liners
########################################################
# Python gives unclear errors if you try to make a one-liner that
# includes multiple lines plus a loop or conditional.
# Because the loop is a compound statement which can't be included
# on the same line with a "small statement" according to Python's grammar:
# https://docs.python.org/reference/grammar.html

# Ways of getting around this:

# Pass the program as stdin:
echo 'import time\nl = range(10)\nfor i in l: print(i)' | python

# Use ANSI quoting n bash, zsh or ksh along with \n:
python -c $'import time\nl = range(10)\nfor i in l: print(i)\n'

# More POSIX compliant: use command substitution:
python -c "$(printf %b 'import sys\nfor r in range(10): print("%d:" % r)')"

# You can also sometimes rewrite loops with list comprehensions or map()
# to turn them into small statements.

########################################################
# Debugging and stack traces
########################################################

# Print a stack trace -- how did we get here?
traceback.print_stack()

# Print a traceback after an exception:
print(traceback.format_exc())

# Equivalent of verbose mode in a shell: print each line before executing.
python -m trace --trace /tmp/foo.py

# Debugging in python2:
print >>sys.stderr, "foo"
# and in python3:
print('foo', file=sys.stderr)

# Suppress stdout and stderr chatter:
sys.stdout = open(os.devnull, "w")
sys.stderr = open(os.devnull, "w")
# This only works for chatter that comes from Python libraries, though.
# For an example that can suppress underlying C libraries,
# see run_main_quietly() at the end of quickbrowse.py.

# Prettyprinting
import pprint
pprint.pprint(obj)

# Binary bit fields to string: all the native ways of printing binary
# in Python insist on signed integers.
def tobin(data, width=8):
    data_str = bin(data & (2**width-1))[2:].zfill(width)
    return data_str

# And, speaking of bit fields, Python's ~ operator is fairly useless
# because it always turns on a sign bit, no matter how large the operand,
# and there's apparently no way to mask it off.
# So instead, use ^0xff (or appropriate length) if you want a bitwise NOT:
>>> ~0xff
-256
>>> 0xff ^ 0xff
0


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

# Fix "UnicodeEncodeError: 'ascii' codec can't encode character":
.encode('utf-8', "xmlcharrefreplace")

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

# Replace non-breaking spaces in unicode (python3):
s = s.replace("\u00A0"," ")

# Split with a regexp:
sep = re.compile('[,\s]+')
sep.split('HB42,SJR1, HR67 SB3')

############################
# Frustrations at exceptions when printing,
# when Python (even Python 3) wants to convert to ascii rather than
# the system encoding:
# I need a test case for this, so save one next time it happens!
# Otherwise, ignore this section, they're just notes to help debug
# next time I hit this problem.

# New in Python 3.7:
sys.stdout.reconfigure(errors='surrogateescape')
# In 3.6, you can get a similar effect with an env variable:
PYTHONIOENCODING=utf-8:surrogateescape

# In Python2, this might also help:
sys.setdefaultencoding('utf8')
# though it's frowned upon:
# https://stackoverflow.com/questions/3828723/why-should-we-not-use-sys-setdefaultencodingutf-8-in-a-py-script/34378962#34378962
# You'd think it would use the system locale by default for printing,
# and quite a few pages claim UTF-8 is the default, but that doesn't
# seem to be true: even in Python 3 I frequently see exceptions
# indicating that for some bizarre reason python3 is trying to
# convert to ascii for printing. And in python3, sys.getdefaultencoding()
# is already utf-8 so that doesn't explain the ascii codec exceptions.

#############################
# Speaking of exception frustrations: here's how to print a traceback
# from the current exception. Curiously, you don't need to pass in the
# actual exception.
traceback.format_exc()

#############################
# All the ways of formatting numbers, from https://stackoverflow.com/a/2962966

# String concatenation:
filename = 'file' + str(num) + '.txt'

# Conversion Specifier:
filename = 'file%s.txt' % num

# Using local variable names:
filename = 'file%(num)s.txt' % locals()  # Neat trick

# Using format():
filename = 'file{0}.txt'.format(num)     # Note: This is the new preferred way

# Using string.Template:
filename = string.Template('file${num}.txt').substitute(locals()))

########################################################
# Byte strings and byte arrays
########################################################

buf = bytearray(b'\x51\x02\x00\x00\x00')
buf.append(0xa2)
buf.insert(2, 0xf7)

# struct: https://docs.python.org/2/library/struct.html
# is perhaps a better way to handle byte strings like this.

########################################################
# iterator, list and dictionary helpers
########################################################

# Remove items from a list: I always forget how to do this.
mylist.remove("item")    # Removes the first instance of "item"
mylist.pop(i)            # Removes and returns list[i]
# There's no single call to remove ALL instances of an item,
# so you have to use a list comprehension to do that.

# Delete an item from a dictionary:
del thedic[key]

# Insert an item into a list BEFORE the given index:
l = ['a', 'b', 'c', 'd', 'e']
l.insert(3, 'xxx')
# --> ['a', 'b', 'c', 'xxx', 'd', 'e']

# List comprehensions can be multiple:
[ a*b+c for a in A for b in B for c in C ]
# though itertools.product is arguably cleaner for math problems like that.

# There are dict comprehensions too though the syntax is more fiddly:
>>> { key: value for key, value in [ (1, 11), (2, 22), (3, 33) ] }
{1: 11, 2: 22, 3: 33}
>>> { key: value for key, value in zip( [1, 2, 3], [11, 22, 33] ) }
{1: 11, 2: 22, 3: 33}

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
# Useful regular expressions
########################################################

# Difference between match and search:
# match matches only from the beginning of the string,
# search will look anywhere in the string.

# Find MAC address:
match = re.search(r'([0-9A-F]{2}[:-]){5}([0-9A-F]{2})', instr, re.I)
if match: return match.group()

# Find IP address:
match = re.search(r'([0-9]{1,3}[\.]){3}([0-9]{1,3})', instr)
if match: return match.group()

########################################################
# Command-line Argument parsing
########################################################
# #python recommends click first (not installed by default),
# then argparse, over optparse.

import argparse

def parse_args():
    """Parse commandline arguments."""
    parser = argparse.ArgumentParser(description="Do some stuff")

    # Boolean flag
    parser.add_argument('-c', "--check", dest="check", default=False,
                        action="store_true", help="Help string")
    # int or string flag.
    # Without type=, will store a string.
    parser.add_argument('-b', action="store", default=2, dest="beta", type=int,
                        help='Beta parameter (default: 2)')

    # Date
    parser.add_argument('-s', "--start", dest="start_date", default=None,
                        help="Start date, YYYY-MM-DD, "
                             "default beginning of this year",
                        type=lambda s: datetime.datetime.strptime(s,
                                                                  '%Y-%m-%d'))

    # Flag that takes multiple arguments, with different names for each arg.
    # Note that this is also a way around the problem of passing
    # an argument that starts with a dash: argparse won't allow strings
    # that start with a dash, thinking they're flags, but if they
    # look like numbers with no extra characters embedded, it will
    # allow them.
    parser.add_argument('-a', '--area', action='store',
                        type=int, nargs=4,
                        dest='area', default=[-180, 180, -70, 74],
                        metavar=("west", "east", "south", "north"),
                        help="Area to plot")

    # single positional argument
    parser.add_argument('url', help='The URL to open')
    parser.add_argument('urls', nargs='?', default='http://localhost/',
                        help="URLs to open")

    # or, multiple arguments requiring at least one
    parser.add_argument('urls', nargs='+', default='http://localhost/',
                        help="URLs to open")

    args = parser.parse_args(sys.argv[1:])
    # Now we have args.check, args.beta, args.url or urls.

    # parse_known_args() is like parse_args() except that it doesn't
    # give an error if you pass extra arguments; instead, it returns
    # a 2-item tuple, consisting of the arg namespace and a list of
    # the remaining args:
    args, rest = parser.parse_known_args(sys.argv)

# Optional argument example:
    parser.add_argument('-n', "--dryrun", dest="dryrun", default=False,
                        action="store_true")
    parser.add_argument('-s', "--sync", dest="sync", default=False,
                        action="store_true")
    parser.add_argument("src")
    parser.add_argument("dst", nargs='?')
    args = parser.parse_args(sys.argv)

# For something more complicated, like different numbers of arguments
# depending on a flag, it's not clear argparse can handle that.
# See androidfiles.py for a sample workaround.

# To allow for newlines in the help strings:
parser = argparse.ArgumentParser(description="Long string\nwith newlines",
                                 formatter_class=argparse.RawTextHelpFormatter)

# Print usage:
parser.print_help()

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

# Beginning of today:
datetime.datetime.now().replace(hour=0, minute=0,
                                second=0, microsecond=0)

# Earliest and latest dates:
datetime.datetime.min, datetime.datetime.max

# Subtracting datetimes gives a datetime.timedelta, and that's also
# a good way to add or subtract time from a datetime.
now = datetime.datetime.now()
if (now - time_end).seconds < 7200:
    time_end = now - datetime.timedelta(seconds=7200)

#
# Parse a date in RFC 2822 format.
#
datetime.datetime.strptime('2016-01-01', '%Y-%m-%d')

# Same thing with decimal seconds:
datetime.datetime.strptime('2016-01-01.234', '%Y-%m-%d.%f')

# datetime to Unix timestamp:
time.mktime(d.timetuple())

# Unix timestamp to datetime:
datetime.datetime.fromtimestamp(1553010256)
datetime.datetime.utcfromtimestamp(1553010256)

# but unfortunately there's no way, with just the Python core,
# to parse a date that might or might not have decimal seconds.
# You have to strip it off in this way, which seems horrifying
# but you'll see it recommended all over, and you'd better hope
# the decimal point is where you expect it and not some other place
# inside the string:
timestr = '2016-01-01.234'
if '.' in timestr:
    d = datetime.datetime.strptime(timestr, '%Y-%m-%d.%f')
else:
    d = datetime.datetime.strptime(timestr, '%Y-%m-%d')

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
# Unfortunately dateutil isn't part of the python core,
# it's a separate package so it adds a dependency.
#
import dateutil.parser
d = dateutil.parser.parse("2012-08-16 14:25:05.265739")
d = dateutil.parser.parse("10/31/2016 14:25")
d = dateutil.parser.parse("6/15/2016 14:25 MDT")
# Also see the Arrow library, a Datetime replacement
# that offers super-general date parsing like "an hour ago".

#
# Calendar.timedelta
#
import datetime
import calendar
today = datetime.date.today()
days_this_month = calendar.monthrange(today.year, today.month)[1]
one_month_from_now = today + datetime.timedelta(days=days_this_month)

# There's also isodate.parse_datetime which I haven't looked into yet.

# Number of days in a month:
calendar.monthrange(year, month)[1]
# monthrange returns weekday of the first day and number of days in the month.

# Or do it using only datatime:
(datetime.datetime(year, month % 12 + 1, 1) - datetime.timedelta(days=1)).day

########################################################
# Threading and multiprocessing
########################################################

# Easy way to schedule something:

# In a single-threaded environment:
import sched, time
def print_time():
    print "From print_time", time.time()

if __name__ == '__main__':
    s = sched.scheduler(time.time, time.sleep)
    s.enter(5, 1, print_time, ())
    s.enter(10, 1, print_time, ())
    s.run()

# In multi-threaded environments:
from threading import Timer
import time

def run_later(a, b):
    print("Hello, it's later now, and time is %f" % time.time())
    print(a, b)

if __name__ == '__main__':
    Timer(5, run_later, (1, 2)).start()
    Timer(11, run_later, (4, 5)).start()
    for i in range(10):
          print(i*2)
          time.sleep(2)

########################################################
# BeautifulSoup
########################################################

Difference between .string and .text:
  .string returns a NavigableString object, which offers a lot of
          the same methods tags do.
  .text returns a unicode object that concatenates  all the child strings.

Useful recent additions: tag.replace_with_children()

# Find tags with inline style attribute:
for t in soup.findAll(style=True)
# Harder way, using lambda:
soup.findAll(lambda tag: 'style' in tag.attrs)

########################################################
# Handling cookies with Requests
########################################################

# To handle cookies with requests, ignore the Requests documentation
# that says to use a RequestCookieJar: that's apparently only for
# setting cookies, not fetching them. Instead, use a Session:
session = requests.Session()
r = session.get(url)

########################################################
# Some handy utility classes
########################################################

# Copying and moving files: shutil.copy and shutil.move

# Handle quoting for something that might need to be passed to a shell:
# in Python 3, shlex.quote() does it, but if it needs to be compatible
# with both 2 and 3, use pipes.quote().

########################################################
# subprocess
########################################################
# Read lines from a subprocess as they appear:
import subprocess

proc = subprocess.Popen(["procname"], stdout=subprocess.PIPE)
while True:
    line = proc.stdout.readline()
    print("line: %s" % line)

# Chain a multi-command pipeline:
p1 = subprocess.Popen([args1],
                      shell=False, stdout=subprocess.PIPE)

p2 = subprocess.Popen([args2],
                      shell=False, stdin=p1.stdout, stdout=subprocess.PIPE)
p1.stdout.close()

p3 = subprocess.Popen([args3],
                      shell=False, stdin=p2.stdout, stdout=subprocess.PIPE)
p2.stdout.close()

p4 = subprocess.Popen([args4].
                      shell=False, stdin=p3.stdout, stdout=subprocess.PIPE)
p3.stdout.close()

output = p4.communicate()[0]


########################################################
# CGI: how to tell if something is run as a CGI or locally
########################################################
if 'REQUEST_METHOD' in os.environ:
    print("Run as CGI", file=sys.stderr)
    form = cgi.FieldStorage()
else:
    print("Run locally")

########################################################
# Conditional import and testing imported libraries
########################################################

try:
    import foo
except:
    pass
import sys

if 'foo' in sys.modules:
    myfoo = foo.Foo()
else:
    myfoo = None

########################################################
# Import of runtime-specified modules and functions
########################################################
modulename = 'MyModule'
functionname = 'TheFunction'

themodule = __import__(modulename)
val = getattr(themodule, functionname)()

########################################################
# OS-specific stuff
########################################################

# Read keys in cbreak mode.
# Some info at:
# http://docs.python.org/2/faq/library.html#how-do-i-get-a-single-keypress-at-a-time
# but it's incomplete, so see
# https://github.com/akkana/scripts/blob/master/keyreader.py
# for a better solution.
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
# sorting + lambda examples
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


################################################################
# Nonlocal variables, class statics, and closures
################################################################

# Class-static variables, more or less:
def f(a):
    try:
        f.numruns += 1
    except AttributeError:
        # First time through
        f.numruns = 1
    # To avoid try/except you can also test if 'numruns' in f.__dict__
    # or hasattr(f, 'numruns')

    print(a, "f has been run %d times" % f.numruns)

f(1)
f(12)
f(42)


# Variables inside an inner function can see outer function variables
# (including parameters) as read-only. Use "nonlocal" to modify them.
# Example:

def outer_fcn():
    thestr = "Set by outer"

    def inner_fcn1():
        print("Inside fcn1:", thestr)

    def inner_fcn2():
        thestr = "Inner function overrode the variable"
        print("Inside fcn2:", thestr)

    def inner_fcn3():
        nonlocal thestr
        thestr = "Changed by inner function"
        print("Inside fcn3:", thestr)

    print("Initially:", thestr)
    inner_fcn1()
    print("After fcn1:", thestr)
    inner_fcn2()
    print("After fcn2:", thestr)
    inner_fcn3()
    print("After fcn3:", thestr)

outer_fcn()

# Note: when inner() is defined inside outer(), every time outer() is called
# there's a small overhead because a function object is created for inner(),
# whether or not it is used.
# To see the overhead, try this nifty trick:
import dis; dis.dis(lambda x: lambda n: x*n)

# A closure is when a nested function references a value in its enclosing scope.
# Closure is basically a limited form of scheme-style static scoping.

# Example:

gGlob = "before print_msg was called"

def print_msg(msg):
    outer_var = "Variable local to print_msg"

    def printer():
        print(msg, '-', outer_var, '-', gGlob)

    return printer

another = print_msg("Hello")
gGlob = "after print_msg was called"
another()

# Output: Hello after print_msg was called
#
# The value of msg was set when print_msg() was called,
# and when another() is run, it's run with a scope where its nonlocal variable,
# msg, is remembered.
# But it's limited: it  doesn't remember global variables from
# outside the function.

# Finding out what's in the closure:
print("Closure:")
for c in another.__closure__:
    print('-', c.cell_contents)


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
# Performance profiling
################################################################

$ python -m cProfile -o profiling_results myscript.py

>>> import pstats
>>> stats = pstats.Stats("profiling_results")
>>> stats.sort_stats("tottime")
>>> stats.print_stats(15)

# or, from the cmdline:

python -c 'import pstats; stats = pstats.Stats("profiling_results"); stats.sort_stats("tottime"); stats.print_stats(15)'

# Or,

import sys, pstats
p = pstats.Stats(filename)
p.sort_stats('time').print_stats(30)

################################################################
# PyEphem
################################################################
# The documentation on angles is completely wrong and misleading.
# Angles can only be created with degrees() or hours()
# but the value passed in is either a string representing degrees
# or hours, or else it's a float representing radians.

>>> seven_from_float = ephem.degrees(7.)
>>> seven_from_str = ephem.degrees('7')
>>> print(seven_from_float, seven_from_str)
401:04:13.6 7:00:00.0
>>> print(seven_from_float.norm, seven_from_str)
41:04:13.6 7:00:00.0
>>> seven_from_radians = ephem.degrees(7 * math.pi / 180.)
>>> print(seven_from_radians)
7:00:00.0

>>> seven_hours_from_radians = ephem.hours(7 * math.pi / 12)
>>> print(seven_hours_from_radians)
7:00:00.00
>>> float(seven_hours_from_radians) * 12 / math.pi
7.0

################################################################
# Matplotlib tips
################################################################

ax1 = fig.add_subplot(2, 1, 1)   # nrows, ncols, plotnum

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

# Exit on key q (this now seems to be the default)
plt.figure(1).canvas.mpl_connect('key_press_event',
                                 lambda e:
                                     sys.exit(0) if e.key == 'ctrl+q'
                                     else None)

# Highlight the X axis, or any other horizontal or vertical line:
ax.axvline(x=42, color='r', linewidth=1)

# Apply a function to a numpy array, returning another array
def wraparound(x):
    if x > 12: return x-24
    return x
vwraparound = np.vectorize(wraparound)
wrapped_arr = vwraparound(orig_arr)

# Dates on X axis rotated a bit, so they don't overwrite each other:
fig.autofmt_xdate()

#
# Custom ticks and labels for dates:
# see plot_curves_by_date() in weather/evebump.py
#


################################################################
# Python3 differences
################################################################

# Migrate python2 to python3 in place (omit -n to leave a .bak):
$ 2to3 -wn file_or_directory

# To make print() work in both 2 and 3:
from __future__ import print_function

# print without a newline and to a file:
print("Hello, world", end='', file=sys.stderr)

# encode/decode between bytes and str:
>>> b'string of bytes'.decode()
'string of bytes'

>>> b'string of bytes'.decode('utf-8')
'string of bytes'

>>> 'piñon'.encode('utf-8')
b'pi\xc3\xb1on'

# For a while, you could just pass encoding as a second argument
# in type coercion; This has changed in more recent python3,
# so don't use it any more.
# I don't know the limits, but it's probably best not to use things like:
>>> str(b'string of bytes')
"b'string of bytes'"
>>> str(b'string of bytes', 'utf-8')
'string of bytes'
>>> str(b'pi\xc3\xb1on')
"b'pi\\xc3\\xb1on'"
>>> str(b'pi\xc3\xb1on', 'utf-8')
'piñon'
>>> bytes('piñon', 'utf-8')
b'pi\xc3\xb1on'

# Read or write bytes from a file:
fp = open(filename, 'rb')   # or 'wb'

# Write bytes to a file opened in string mode with .buffer
if hasattr(sys.stdout, 'buffer')::
    sys.stdout.buffer.write(b'abc')

# Also, you can specify encoding when opening a file:
open(path, "w", encoding="utf-8")

# Conditional depending on python version:
if sys.version[:1] == '2':
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

# Call input everywhere but make that call raw_input if it's python2:
try: input = raw_input
except NameError: pass
# OR:
if hasattr(__builtins__, 'raw_input'):
    input = raw_input

################################################################
# Type hinting
################################################################

'''
Several ways of hinting about types in Python 3:
Type hinting with the typing module:
  https://docs.python.org/3/library/typing.html

Function annotations, PEP 3107:
  https://www.python.org/dev/peps/pep-3107/

Some related tools:
MyPy: an experimental optional static type checker (uses type hints)
  http://mypy-lang.org/
PySonar: a type inferencer and indexer
  https://yinwang0.wordpress.com/2010/09/12/pysonar/
'''

################################################################
# pip hints
################################################################

'''
Pip reinstall:
    pip install -I
--force-reinstall isn't enough, you need --upgrade which is -I

Get a list of installed files:
Basically, you can't. pip show -f packagename
gives a Location which may or may not
be where every file in the package ends up.
pip uninstall packagename does give the full list, but there's no -n
option so you have to actually install the package to see the file list.
'''
