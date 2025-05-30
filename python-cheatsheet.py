#!/usr/bin/env python

# This is a file of reminders of various neat Python features
# that I always forget how to use.

# On #python as of early 2017, recommended beginning Python books include
# http://greenteapress.com/wp/think-python-2e/
# https://automatetheboringstuff.com/
# (the oft-recommended "Learn Python the Hard Way" is not well favored).
# I can't vouch for these books myself.
# For intermediates, I've seen Fluent Python recommended on #python.

########################################################
# Interactive Python interpreter
########################################################

# modulename isn't quoted, and is the name you're using
# e.g. if import modulename as mn, then imp.reload(mn)

# Python 3.4 and later:
import importlib
importlib.reload(modulename)

# importlib is also useful for importing a module named by a variable, e.g.
modname = 'requests'
importlib.import_module(modname)

# Python 3.2 - 3.3:
import imp
imp.reload(modulename)

# in python2 it was built in:
reload(modulename)

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

# Where is this script located?
__file__

# ChainMap looks something up in a series of dict-like variables:
pylookup = ChainMap(locals(), globals(), vars(builtins))

# Or, more generally,
try:
    myVar
except NameError:
    myVar = None

# Is something a particular type? (But of course duck-typing is better.)
if type(s) is str:
    print("It's a string")
if isinstance(s, str):
    print("It's a string")

# More deprecated:
if type(s) == types.StringType:
    print "It's a string"

# Is something list-like, iterable?
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

# Initialize a list to multiple copies of something.
# DON'T USE l = [ [] ] * 10  -- you'll get ten copies of the same list!
# Instead,
l = [ [] for i in range(10) ]

# There is no such thing as Maximum/minimum integers any more.
# https://docs.python.org/3.1/whatsnew/3.0.html#integers
"""The sys.maxint constant was removed, since there is no longer a limit
to the value of integers. However, sys.maxsize can be used as an integer
larger than any practical list or string index. It conforms to the
implementation\u2019s \u201cnatural\u201d integer size and is typically
the same as sys.maxint in previous releases on the same platform
(assuming the same build options)."""

# Also from that page, PEP 0238:
"""An expression like 1/2 returns a float. Use 1//2 to get the
truncating behavior."""

# Maximum/minimum floats
>>> sys.float_info.max
1.7976931348623157e+308
>>> sys.float_info.min
2.2250738585072014e-308

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
# Using global variables from an import
########################################################

# This works:
import stuff

def main():
    stuff.VERBOSE = True
    stuff.do_stuff()

# This doesn't:
from stuff import VERBOSE, do_stuff

def main2():
    VERBOSE = True
    do_stuff()

'''
<SnoopJ>  akk, when you do `from stuff import VERBOSE`, you create a new name in [whatever module you're in] called `VERBOSE` whose value is the same as `stuff.VERBOSE` *at import time*. But otherwise they are unrelated.
<akk> SnoopJ: Ah, so it's set at import time to whatever stuff.VERBOSE was at that point, but it's just a copy local to the file?
<SnoopJ>  akk, right, they are separate names
<SnoopJ> `from somewhere import something` is almost like writing `import somewhere; something = somewhere.something; del somewhere`
<SnoopJ> There's a great explanation of the broader mechanisms here: https://nedbatchelder.com/text/names1.html
'''

########################################################
# Import of runtime-specified modules and functions
########################################################

modulename = 'MyModule'
functionname = 'TheFunction'

themodule = __import__(modulename)
val = getattr(themodule, functionname)()

# Also, a note on importing:
# "from pytopo import user_agent" makes a copy of
# the variable and doesn't see later changes.
# If you want to see changes, you need to
# import pytopo and have it be pytopo.user_agent.

# Testing a single file in a submodule:
python -m app.bills.nmlegisbill
# The python -m is needed, and note .py has been dropped from the filename.


########################################################
# Shell One-liners
########################################################
# Python gives unclear errors if you try to make a one-liner that
# includes multiple lines plus a loop or conditional.
# Because the loop is a compound statement which can't be included
# on the same line with a "small statement" according to Python's grammar:
# https://docs.python.org/reference/grammar.html

# Ways of getting around this:

# Pass the program as stdin:
echo 'import time\nl = range(10)\nfor i in l: print(i)' | python

# Combining semicolons (e.g. from an import line) and a for loop
# doesn't work, syntax error.
# https://stackoverflow.com/questions/2043453/executing-multi-line-statements-in-the-one-line-command-line
# Instead, use ANSI quoting in bash, zsh or ksh along with \n:
python -c $'import time\nl = range(10)\nfor i in l: print(i)\n'

# More POSIX compliant: use command substitution:
python -c "$(printf %b 'import sys\nfor r in range(10): print("%d:" % r)')"

# You can also sometimes rewrite loops with list comprehensions or map()
# to turn them into small statements.

########################################################
# Debugging and stack traces
########################################################

# Dump into the debugger (in 3.7 and later):
breakpoint()

# Print line by line tracing
sys.settrace()

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
from pprint import pprint
pprint(obj)

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

# Print a listing of variables along with a traceback: see
# http://code.activestate.com/recipes/52215-get-more-information-from-tracebacks/

########################################################
# Stringy stuff (Python 3)
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

# Detect charset if you don't know it:
>>> chardet.detect(b'\301\242\300\200\300\231')
{'encoding': 'Windows-1252', 'confidence': 0.73, 'language': ''}
>>> b'\301\242\300\200\300\231'.decode('Windows-1252')
'Á¢À€À™'

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

# Convert a character (e.g. pasted from somewhere) to a
# hex unicode codepoint that you can insert inside a string.
print('%x' % ord('█'))    # --> 2588
hex(ord('█'))             # --> '0x2588'
print("Here is the character again: \u2588")

# s.find vs s.index: find returns -1 if not found, index raises ValueError

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
    r = SequenceMatcher(None, pattern, b).ratio()
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

# raw string literals: r'' avoids any backslash escapes.
# printf-style %x still works, e.g. r'abc %d' % 42
r = r'abc\def'
c = 'abc\\def'
r == c    # True


# Replace non-breaking spaces in unicode:
s = s.replace("\u00A0"," ")

#############
# Some Python 2 stuff that might still apply (test first):

# Detect charset if you don't know it:
>>> chardet.detect(b'\301\242\300\200\300\231')
{'encoding': 'Windows-1252', 'confidence': 0.73, 'language': ''}
>>> b'\301\242\300\200\300\231'.decode('Windows-1252')
'Á¢À€À™'

# s.find vs s.index: find returns -1 if not found, index raises ValueError

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
    r = SequenceMatcher(None, pattern, b).ratio()
    if r > best_ratio:
        best_match = b
        best_ratio = r

################################################################
# re: Regular expressions/regexp:
################################################################

""" For parsing, consider using something other than an f-string:
    for HTML, use BeautifulSoup; for things with more pythonic syntax,
    use json.loads() or ast.literal_eval()
"""

# Build up expressions using f-strings:
# https://death.andgravity.com/f-re

# Some useful regexp builders:
# https://regex-generator.olafneumann.org/
# https://regex101.com/ (but doesn't allow pasting)

# re match vs search:
# match matches only from the beginning of the string,
# search will look anywhere in the string.

# Split with a regex:
sep = re.compile('[,\s]+')
sep.split('HB42,SJR1, HR67 SB3')

# Split on multiple characters at once
re.split(', |_|-|!', thestring)
# same, but find words:
re.findall(r"[\w']+", thestring)

# Match patterns even across newlines:
re.search('[0-9]+\..*[A-Z]+', teststr, flags=re.DOTALL)
# Unintuitively, re.DOTALL is the flag that controls this.
# re.MULTILINE controls whether ^ and $ match line beginnings
# and ends in the pattern, but doesn't affect whether the
# search can cross newlines.

# Non-greedy, use ( ... ?)
quoted = re.findall(r"'(.*?)'", buffer, re.DOTALL)

# Grouping without capturing: use (?: ... ) e.g.
re.match(r'''\s*([a-zA-Z]+)\s*(?:([a-zA-Z]+)\s*=\s*(.*))?''',
         '  div class="green"  ')
# the class=green part is optional because of the enclosing (?: )
# but if it's there, we can capture class and green inside it.

# Transliteration:
# https://docs.python.org/3/library/stdtypes.html#str.maketrans
abc = "abc"
abc.translate(abc.maketrans("abc", "def"))
#  If there is a third argument, it must be a string, whose characters
# will be mapped to None in the result.
# You can also pass it a dictionary, but the keys are int, not str.
abc.translate({ord('a'): 'A', ord('b'): None})
# But you can dispense with the ord()s if you call maketrans:
abc.translate(abc.maketrans({'a': 'A', 'b': None}))
# There doesn't seem to be any simple equivalent to perl y/A-Z/a-z/
# -- you can set up ranges with lambdas or comprehensions
# but it gets hairy quickly.

# Use implicit string literal concatenation to make regexps easier to read:
PERCENTPAT = re.compile(
    r"(^|\s)"    # beginning of string or whitespace
    r"%[a-z\d]"  # remind time directive, e.g. %k
    r"($|:|\s)"  # end of string, colon, or whitespace
)

# Replace matched groups:
re.sub('(DP(?:/a){0,1})(-)([A-Z]{3,})', r'\g<1> Sent to \g<3>', 'DP/a-HAFC')
'DP/a Sent to HAFC'


########################################################
# Useful regular expressions
########################################################

# Find MAC address:
match = re.search(r'([0-9A-F]{2}[:-]){5}([0-9A-F]{2})', instr, re.I)
if match: return match.group()

# Find IP address:
match = re.search(r'([0-9]{1,3}[\.]){3}([0-9]{1,3})', instr)
if match: return match.group()


########################################################
# Text wrapping
########################################################

import textwrap
textwrap.fill(intext, width=w)



####### Exceptions #####################

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


# Speaking of exception frustrations: here's how to print a traceback
# from the current exception. Curiously, you don't need to pass in the
# actual exception.
print(traceback.format_exc())


# When raising
# Avoid "During handling of the above exception, another exception occurred":

try:
    some_operation()
except (SomeError, OtherError) as e:
    raise MyCustomException(e, "My custom exception") from None
# Or pass information about the inner exception:
    raise MyCustomException(e, "My custom exception",
                            traceback.format_exc()) from None
    raise MyCustomException(e, "My custom exception",
                            traceback.extract_stack()) from None


########################################################
# iterator, list and dictionary helpers
########################################################

# Remove/delete items from a list: I always forget how to do this.
mylist.remove("item")    # Removes the first instance of "item"
mylist.pop(i)            # Removes and returns list[i]
# There's no single call to remove ALL instances of an item,
# so you have to use a list comprehension to do that.

# iterator unpacking (aka tuple unpacking) doesn't have to use all vals:
>>> a, b, *rest = range(5)
>>> a
0
>>> b
1
>>> rest
[2, 3, 4]

# multiple "with" context managers:
with open("infile") as infile, open("outfile") as outfile:
with A() as a, B() as b, C() as c:

# First item in an ordered dict (or other iterable):
def first(s):
    '''Return the first element from an ordered collection
       or an arbitrary element from an unordered collection.
       Raise StopIteration if the collection is empty.
    '''
    return next(iter(s))

# get first or next item in an iterator:
next(iter)

# Get the next item in the middle of a loop:
listiter = iter(mylist)
for val in listiter:
    if val == 42:
        val = next(iter)
        val = next(iter, None)  # to avoid a StopIteration exception

# Eliminate duplicates from a list.
# Converting to set and back would do it, but can mess up the order
# since there's no ordered set class.
thelist = list(dict.fromkeys(thelist))

# () turns a list comprehension into a generator:
>>> ( i*2 for i in range(5) )
<generator object <genexpr> at 0x7f8fc17db050>

# Dictionary comprehensions:
({i : chr(65+i) for i in range(4)}
 # gives {0: 'A', 1: 'B', 2: 'C', 3: 'D'}

# Delete an item from a dictionary:
del thedic[key]

# Rename a dictionary key:
thedic["new_key"] = thedic.pop("old_key")

# flatten a list using a double comprehension:
x = [[1,2,3],[4,5,6,7],[8,9]]
[i for j in x for i in j]
[1, 2, 3, 4, 5, 6, 7, 8, 9]

# Another flatten:
# l1 = [[1,2,3],[4,5,6,7],[8,9]]
# l2 = []
# for lz in l1:
#      l2.extend(lz)
# l2 -is now [1,2,3,4,5,6,7,8,9]

# flatten using itertools.chain:
# >>> lst = [[1,2,3],[4,5,6,7],[8,9]]
# >>> list(itertools.chain.from_iterable(lst))
# [1, 2, 3, 4, 5, 6, 7, 8, 9]

# Insert an item into a list BEFORE the given index:
l = ['a', 'b', 'c', 'd', 'e']
l.insert(3, 'xxx')
# --> ['a', 'b', 'c', 'xxx', 'd', 'e']

# List comprehensions can be multiple:
[ a*b+c for a in A for b in B for c in C ]
# though itertools.product is arguably cleaner for math problems like that.

# Comprehensions can also have 'if' expressions, but the syntax
# is a little tricky and inconsistent. A conditional with no "else"
# must come at the end, after the list, but a conditional with an else
# may come before the list.
nums = [1, 2, 3, 4, 5]
odds = [n for n in nums if n%2]
isodd = ['t' if n%2 else 'f' for n in nums]

# There are dict comprehensions too though the syntax is more fiddly:
>>> { key: value for key, value in [ (1, 11), (2, 22), (3, 33) ] }
{1: 11, 2: 22, 3: 33}
>>> { key: value for key, value in zip( [1, 2, 3], [11, 22, 33] ) }
{1: 11, 2: 22, 3: 33}

#########################################
# dictionary default values, several ways:

# With regular dicts, you can use get() with a default value
total['newvalue'] = total.get(key, 0) + 42

# With collections, you can use defaultdict
from collections import defaultdict
total = defaultdict(int)
total['newvalue'] += 42

names = defaultdict(list)

# Or if writing a class that inherits from dict, you can define __missing__.
# dict knows about __missing__ and will use it if it's defined,
# though it's not defined by defaults.
class MyDict(dict):
    def __missing__(self, key):
        print("missing key", key)
        return 0
>>> md = MyDict({'one': 1, "three": 3})
>>> md
{'one': 1, 'three': 3}
>>> md['one']
1
>>> md['two']
missing key two
0

# Fluent Python says it's easier to subclass collections.UserDict than dict,
# but apparently that's no longer true and now there's really no need for
# UserDict and UserList. Nobody seems very clear on why it was needed,
# but apparently it hasn't been needed since Python 2.2.

# While we're looking at collections, another useful collection is:
from collections import namedtuple
Point = namedtuple('Point', ['x', 'y'])
p = Point(11, y=22)
print(p.x, p.y)

EmployeeRecord = namedtuple('EmployeeRecord',
                            'name, age, title, department, paygrade')
import csv
for emp in map(EmployeeRecord._make, csv.reader(open("employees.csv", "rb"))):
    print(emp.name, emp.title)


# Pairwise loops with zip():
names = ["Eiffel Tower", "Empire State", "Sears Tower"]
heights = [324, 381, 442]
for name, height in zip(names, heights):
    print("%s: %s meters" % (name, height))

# Same thing with enumerate:
for i, (name, height) in enumerate(zip(names, heights)):
    print("%d: %s: %s meters" % (i, name, height))

# Or make a dictionary from a zip of two lists:
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
# Walk a directory tree with os.walk
#
def walkfiles(rootdir):
    for root, dirs, files in os.walk(rootdir):
        for f in files:
            print(os.path.join(root, f))

# Depth-first, so it's possible to rename directories:
os.walk(root, topdown=False)

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
# Class Properties
########################################################

# Properties let you define a class Rectangle
# and call rect.width and rect.height but have them call a function.

# Explicitly defining properties:
# https://github.com/PacktPublishing/Expert-Python-Programming_Second-Edition/blob/master/chapter3/properties_explicit.py

# Simpler syntax with decorators:
# https://github.com/PacktPublishing/Expert-Python-Programming_Second-Edition/blob/master/chapter3/properties_decorator.py

########################################################
# Command-line Argument parsing
########################################################

def parse_args():
    """Parse commandline arguments."""
    import argparse

    parser = argparse.ArgumentParser(description="Do some stuff")

    # Boolean flag (don't use type=bool, gives a TypeError)
    parser.add_argument('-c', "--check", dest="check", default=False,
                        action="store_true", help="Help string")

    # int or string argument.
    # Without type=, will store a string.
    # For a mandatory argument, add required=True.
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

    # Multiple arguments
    parser.add_argument('urls', nargs='?', default='http://localhost/',
                        help="URLs to open")

    # or, multiple arguments requiring at least one.
    parser.add_argument('urls', nargs='+', default='http://localhost/',
                        help="URLs to open")

    # nargs can also be an integer, but usage statements will repeat
    # the argument name N times, e.g. this will say "coords coords"
    # so be sure to have a good help string as well.
    # If using numeric types, argparse is smart enough to allow negative vals.
    parser.add_argument('coords', nargs=2, type=float,
                        help="longitude latitude in decimal degrees")

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
# built-in help
########################################################

# Save help to a string, without a lot of formatting crap:
import pydoc
helptxt = pydoc.render_doc(Pango, renderer=pydoc.plaintext)
with open("pangodoc.txt", 'w') as fp:
    fp.write(helptxt)


########################################################
# Dates and times
########################################################

# Converting between various date/time formats,
# from https://docs.python.org/3/library/time.html :
From                       To                        Use
----                       ----                      ------
seconds since the epoch    struct_time in UTC        gmtime()
seconds since the epoch    struct_time in localtime  localtime()
seconds since the epoch    datetime (localtime)      datetime.fromtimestamp()
seconds since the epoch    datetime (utc)            datetime.utcfromtimestamp()
struct_time in UTC         seconds since the epoch   calendar.timegm()
struct_time in local time  seconds since the epoch   time.mktime()
datetime                   date                      d.date()
date                       datetime                  datetime.datetime.combine(d, datetime.datetime.min.time())
datetime                   struct_time               dt.timetuple()
datetime                   seconds since the epoch   time.mktime(dt.timetuple()))
# More conversions:
# https://www.saltycrane.com/blog/2008/11/python-datetime-time-conversions/

# Printing formats:
>>> dt = datetime.datetime.now()
>>> dt.strftime("%Y-%m-%d %H:%M")
'2019-07-22 19:46'
>>> dt.isoformat()
'2019-07-22T19:46:20.164427'
>>> f"{dt:%Y-%m-%d %H:%M}"        # Only in Python >= 3.6
'2019-07-22 19:46'

# for no zero padding, add a dash:
>>> d.strftime("%H:%M")
'09:30'
>>> d.strftime("%-H:%M")
'9:30'

######################
# Datetime Arithmetic
######################

# Subtracting datetimes gives a datetime.timedelta, and that's also
# a good way to add or subtract time from a datetime.
now = datetime.datetime.now()
if (now - time_end).seconds < 7200:
    time_end = now - datetime.timedelta(seconds=7200)

# You can define a timedelta with arguments of weeks, days,
# hours, minutes, seconds, milliseconds or microseconds,
# but once you have a timedelta you can only query for
# days, seconds or microseconds.
>>> td = timedelta(hours=36)
>>> td.hours
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
AttributeError: 'datetime.timedelta' object has no attribute 'hours'
>>> td.days
1
>>> td.seconds


# Setting fixed parts of datetime
dt = dt.replace(hour=11, minute=59)

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
# relativedelta offers years, months, weeks, days, hours,
# minutes, seconds, microseconds

def nextmonth(d):
    '''Beginning of the following month.
    '''
    month = d.month + 1
    year = d.year
    if month > 12:
        month = 1
        year += 1
    return d.replace(day=1, month=month, year=year)

# Beginning of today:
datetime.datetime.now().replace(hour=0, minute=0,
                                second=0, microsecond=0)

# Earliest and latest dates:
datetime.datetime.min, datetime.datetime.max

#
# Calendar.timedelta
#
import datetime
import calendar
today = datetime.date.today()
days_this_month = calendar.monthrange(today.year, today.month)[1]
one_month_from_now = today + datetime.timedelta(days=days_this_month)

# Number of days in a month:
calendar.monthrange(year, month)[1]
# monthrange returns weekday of the first day and number of days in the month.

# Or do it using only datetime:
(datetime.datetime(year, month % 12 + 1, 1) - datetime.timedelta(days=1)).day

## Human-readable string for a time interval.
# Cute trick: use time.gmtime directly on the interval.
# Also, I can't find this in the documentation, but adding a - after the %
# omits the zero prefix.
time.strftime("%-d days %-H hours %-M minutes %-S seconds",
              time.gmtime(timesecs))

########################
# time module Arithmetic
########################

time.time() just returns a float, so you can add seconds:
time.time() + 3600
# but you have to turn it into a tuple to format it,
# using functions localtime() or gmtime()
time.strftime("%H:%M", time.localtime(time.time() + 3600))

###############
# Date Parsing
###############

# Parse a date in RFC 2822 format.
#
datetime.datetime.strptime('2016-01-01', '%Y-%m-%d')

# Same thing with decimal seconds:
datetime.datetime.strptime('2016-01-01.234', '%Y-%m-%d.%f')

# To parse AM/PM, use %I %p instead of %H:
datetime.strptime('3/14/2025\t5:23 PM MST', '%m/%d/%Y\t%I:%M %p MST')

# datetime to Unix timestamp:
time.mktime(d.timetuple())

# Unix timestamp to datetime:
datetime.datetime.fromtimestamp(1553010256)
datetime.datetime.utcfromtimestamp(1553010256)

# Unfortunately there's no way, with just the Python core,
# to parse a date that might or might not have decimal seconds.
# You have to strip it off in this way, which seems horrifying
# but you'll see it recommended all over, and you'd better hope
# the decimal point is where you expect it and not some other place
# inside the string (for a comma you'd need an extra clause):
timestr = '2016-01-01.234'
if '.' in timestr:
    d = datetime.datetime.strptime(timestr, '%Y-%m-%d.%f')
else:
    d = datetime.datetime.strptime(timestr, '%Y-%m-%d')

# email.utils.parsedate returns a tuple.
# But be warned it can only parse a full date/time, not just a date,
# even though the time part of the tuple generally isn't correct.
t = time.mktime(email.utils.parsedate("Thu, 11 Aug 2016 14:46:50 GMT")))
(y, m, d, h, m, s, weekday, yearday, isdst) = t
# the last three items of the tuple aren't very useful: typically 0, 1, -1.
# -1 means "unknown" for the dst flag.
secs_since_epoch = time.mktime(t)

t2 = time.mktime_tz(email.utils.parsedate("Thu, 11 Aug 2016 14:46:50 GMT")))
(y, m, d, h, m, s, weekday, yearday, isdst, offset_from_utc) = t2
secs_since_epoch = email.utils.mktime_tz(t2)

# Epoch to struct time:
>>> unixtime = time.time()
>>> time.gmtime(unixtime)
time.struct_time(tm_year=2021, tm_mon=6, tm_mday=8, tm_hour=1, tm_min=6, tm_sec=24, tm_wday=1, tm_yday=159, tm_isdst=0)
>>> time.localtime(unixtime)
time.struct_time(tm_year=2021, tm_mon=6, tm_mday=7, tm_hour=19, tm_min=6, tm_sec=24, tm_wday=0, tm_yday=158, tm_isdst=1)

#
# Parse a date in unknown format into a datetime.datetime object
# Unfortunately dateutil isn't part of the python core,
# it's a separate package so it adds a dependency.
# But it's more reliable than email.utils.parsedate.
#
import dateutil.parser
d = dateutil.parser.parse("2012-08-16 14:25:05.265739")
d = dateutil.parser.parse("10/31/2016 14:25")
d = dateutil.parser.parse("6/15/2016 14:25 MDT")

# There's also isodate.parse_datetime which I haven't looked into yet.

# Arrow is a Datetime replacement that offers humanize()
# to turn a date into something like "an hour ago",
# but it doesn't offer similar services for parsing.

############
# Timezones:
############

# Get the aware current local time in the local timezone:
from datetime import datetime
localnow = datetime.now().astimezone()
# dt.astimezone(tz=None) adjusts to the specified timezone,
# defaulting to the local one. tz would be a tzinfo object.
# If dt is unaware, it's presumed to be local, which is why this works.

# and then you can convert other times into that timezone:
localtz = localnow.tzinfo
localtime = othertime.astimezone(localtz)

# Note that datetime's strptime cannot parse timezone names --
# don't be misled by the documentation mentioning %Z, it lies.
# strftime can print %Z but strptime can't parse it, except UTC.

# Advice from the datetime maintainer Paul Ganssle on Talk Python to Me:
# https://talkpython.fm/episodes/show/271/unlock-the-mysteries-of-time-pythons-datetime-that-is
# https://blog.ganssle.io/
#
# recommends not using pytz (which will be dropped in 2 years).
# Instead, using the new zoneinfo coming in with python 3.9.
# (backport in pypi), or use dateutil.tz

# Don't create a datetime using tzinfo=! It will give the wrong result:
>>> dt.datetime(year=2021,month=6,day=25,hour=10,minute=0,tzinfo=pytz.timezone("America/New_York")).astimezone(dt.timezone.utc)
datetime.datetime(2021, 6, 25, 14, 56, tzinfo=datetime.timezone.utc)
# Instead, you can do one of these:
>>> dt.datetime(year=2021,month=6,day=25,hour=10,minute=0).astimezone(pytz.timezone("America/New_York")).astimezone(dt.timezone.utc)
datetime.datetime(2021, 6, 25, 16, 0, tzinfo=datetime.timezone.utc)
>>> pytz.timezone("America/New_York").localize(dt.datetime(2021,6,25,10)).astimezone(pytz.utc)
datetime.datetime(2021, 6, 25, 14, 0, tzinfo=<UTC>)

# A datetime.tzinfo object is a set of rules that include when to switch
# between DST and ST; it's not just an offset.
from dateutil import tz
MT = tz.gettz("America/Denver")

# Timezones have names, but getting them requires a date:
time_winter = datetime(2020, 2, 14, 12, tzinfo=MT)
MT.tzname(time_winter)
# -> 'MST'
time_summer = datetime(2020, 7, 14, 12, tzinfo=MT)
MT.tzname(time_summer)
# -> 'MDT'
# But see above comment about not using tzinfo= in the constructor.

# Don't use utcnow or utcfromtimestamp in modern python.
# They might even be deprecated soon. Instead:
from datetime import timezone
utcnow = datetime.now(tz=timezone.utc)
datetime.fromtimestamp(1571595618.0, tz=timezone.utc

# Take an unaware UTC datetime, like what comes from ephem.Date.datetime()
# and make it aware:
utctime = observer.date.datetime.replace(tzinfo=timezone.utc))
# Note that despite what "replace" might imply, this does not
# replace anything in the original object, merely creates a new copy.

# Check if a datetime is timezone aware:
t = datetime.strptime("2022-06-09 11:23 MDT", "%Y-%m-%d %H:%M %Z")
t.tzinfo                # -> None if unaware
datetime.utcoffset(t)   # -> None if unaware

# All pytz code should be migrated over to zoneinfo or dateutil
# and get on the PEP495 bandwagon.
# PEP 495: Local time disambiguation: https://www.python.org/dev/peps/pep-0495/
# https://www.python.org/dev/peps/pep-0495/
# PEP 615: Support for the IANA Time Zone Database in the Standard Library
# https://www.python.org/dev/peps/pep-0615/

# Aware datetime arithmetic:
# https://blog.ganssle.io/articles/2018/02/aware-datetime-arithmetic.html
from datetime import datetime, timedelta
ET = tz.gettz("America/New York")
noon_mt = datetime(2020, 7, 4, 12, tzinfo=MT)
noon_et = datetime(2020, 7, 4, 12, tzinfo=ET)
noon_mt - noon_et
# -> datetime.timedelta(seconds=7200)
# Keep in mind that timedeltas don't include any timezone info themselves.

# dateutil will handle timezones in ical format (it's also good at parsing)
# and it has rrules for recurrences. It also has Easter.
# arrow has humanize, which can give you strings like "an hour ago".
# Pendulum is slow and not fully backward compat with datetime: don't use.
# But Michael Kennedy likes pendulum because it can give you aware
# timedeltas that you can subtract, and iterators over things like weekdays.

# Some reasons not to use pytz:
# https://blog.ganssle.io/articles/2018/03/pytz-fastest-footgun.html

# Brandon Rhodes, the author of PyEphem and Skyfield, uses pytz
# because it's compatible with Python2, which doesn't have dateutil
# or datetime.now().astimezone() with no argument.

################################################################
# Pathlib, cross-platform replacement for os.path and much more.
# https://docs.python.org/3/library/pathlib.html
# https://treyhunner.com/2018/12/why-you-should-be-using-pathlib/
# https://treyhunner.com/2019/01/no-really-pathlib-is-great/
################################################################

>>> from pathlib import Path, PosixPath

# For paths in Python3=only projects, consider using pathlib rather than os.path
# https://docs.python.org/3/library/pathlib.html#pathlib.Path
Path.home()    # the user's homedir

>>> rock =  Path('~', 'Music', 'Rock').expanduser()
>>> rock
PosixPath('/home/akkana/Music/Rock')
>>> g = rock.rglob('*.mp3')
>>> g
<generator object Path.rglob at 0x7f630d9e48d0>
>>> list(g)
# ... list of PosixPath objects
# rglob is recursive, glob is nonrecursive unless the pattern starts with **/
# which means “this directory and all subdirectories, recursively”.

>>> p = Path()
>>> p
PosixPath('.')
>>> p.resolve()
PosixPath('/home/username/pathlib')

# Other methods include .mkdir(), .rmdir(), .unlink().rename(), .exists(),
# .is_dir(), .is_file(), .stat(), .iterdir(),
# .open(), .read_bytes(), .read_text(), .write_bytes(), .write_text()
  # reads and writes don't require open first

Path('.editorconfig').write_text('# config goes here')

path = Path('.editorconfig')
with path.open(mode='wt') as config:
    config.write('# config goes here')

# 3.6 on:
path = Path('.editorconfig')
with open(path, mode='wt') as config:
    config.write('# config goes here')


# Use pathlib to search the filesystem:
for filename in Path('/').rglob('*.py'):
    print(filename)

########################################################
# subprocess
########################################################

# Read lines from a subprocess as they appear, both stdout and stderr:
outstring = subprocess.check_output(arglist)

# To suppress stderr, add stderr=subprocess.DEVNULL
# stdout can't be redirected with check_output.
# To capture only stderr:
output = subprocess.run(arglist, stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE).stderr

# More complicated way:
import subprocess

proc = subprocess.Popen(["cmd", "arg"], check=True, stdout=subprocess.PIPE)
# check raises  CalledProcessError if the subprocess exits != 0
while True:
    line = proc.stdout.readline()
    if not line:
        break
    print("line: %s" % line)

proc = subprocess.run(["cmd", "arg"], capture_output=True)
# CompletedProcess(args=['ls', '-l', '/dev/null'], returncode=0,
# stdout=b'crw-rw-rw- 1 root root 1, 3 Jan 23 16:23 /dev/null\n', stderr=b'')

# Pass input from a bytes object, then read output as another bytes object.
proc = subprocess.Popen(["/usr/bin/remind", "-n", "-" ],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
outputbytes = proc.communicate(input=inputbytes)[0]

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
# communicate() runs the command, reads all output and waits for it to finish
# (it can also take a timeout).

#
# Exclusive mode: run only one instance of a process
#
# Method 1: loop over pids in /proc, looking for a matching name.
#           see find_proc_by_name() in quickbrowse.py
# Method 2: use file locking.
#           The filelock module doesn't actually lock, so instead,
#           use fcntl.lockf(f, fcntl.LOCK_EX|fcntl.LOCK_NB)
#           see https://stackoverflow.com/a/46407326
#           LOCK_NB means anyone else trying to open the file will raise
#           BlockingIOError: [Errno 11] Resource temporarily unavailable;
#           if it's omitted, anyone trying to open the file will block.
#           This is a mess, though. You can't call fcntl.lockf until
#           you've already opened the file, so if you're on a filesystem
#           where file-locking doesn't work, opening it in write mode
#           will zero it out.

########################################################
# inter-process communication
########################################################

#### Named pipes are easy when you only need to talk in one direction.
# See namedpipe.py for a working example.

#### If you need it bidirectional, Unix domain sockets are the answer,
#### but are a little harder to use. See eggtimer.py for a working example.
#### quickbrowse also has an example, but that one's unidirectional.

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
# CSV
########################################################

with open(filename) as csvfp:
    reader = csv.DictReader(csvfp)
    for row in reader:
        # Each row is an OrderedDict

########################################################
# Use the same StringIO for both input and output
########################################################

from io import StringIO
outfp = StringIO()
csvwriter = csv.writer(outfp)
csvwriter.writerow(outfields)
for row in csvreader:
    csvwriter.writerow(row)

outfp.seek(0)
reader = csv.DictReader(csvfp)
...

########################################################
# BeautifulSoup
########################################################

"""
Difference between .string and .text:
  .text returns a unicode object that concatenates  all the child strings.
  .string returns a NavigableString object, which offers a lot of
          the same methods tags do.
          It gets the string from something that has a single NS child,
          e.g. href or title, or something that has only one child
          and that child has only a single NS child.
          .string will be None if there are multiple NS descendants.
  .strings and stripped_strings iterate over all string children.

Useful recent additions: tag.replace_with_children()

Whitespace:
tag.find_next_sibling() and find_previous_sibling() will skip over
intervening NavigableString whitespace, whereas tag.next_sibling
and tag.previous_sibling will return the whitespace.
"""

# Iterate depth-first over all tags: soup.find_all()

# Iterate over all parents, going uphill:
for parent in link.parents: ...

# Find tags with inline style attribute:
for t in soup.find_ll(style=True)

# Find tags with inline absolute positioning style
P_ABSOLUTE = re.compile(r'position:\s*absolute')
soup.find_all('p', style=P_ABSOLUTE)

# Harder way, using lambda:
soup.find_all(lambda tag: 'style' in tag.attrs)

# Remove a tag and its children.
tag.decompose()
# Use decompose() rather than extract():
# tag.extract() removes a tag from the tree and returns it.
# tag.decompose() removes it from the  tree and deletes it and its contents.

# Remove a tag but keep what's inside it:
for tag in invalid_tags:
    for match in soup.find_all(tag):
        match.replaceWithChildren()

# Get first child
child = next(tag.children)

# Delete all children:
tag.clear()

# Iterate over ALL children: for c in tag.children only shows nodes,
# but iterating over contents (a list) gives nodes AND NavigableStrings.
for c in soup.em.contents:
    print("::", c.name, "::", type(c), "::", c)
# To recurse into sub-children, use .descendants, which does
# include NavigableStrings.

# .next_sibling and .previous_sibling include strings, not just tags.
# Also, you can get an iterator over all future/past siblings:
for sibling in soup.a.next_siblings: ...

# The section on contents in
# https://beautiful-soup-4.readthedocs.io/en/latest/#modifying-the-tree
# implies that .children is just an iterator over .contents, but it's not:
# .children only gives tags, .contents gives tags AND NavigableStrings.

# Finding out about clear() was a relief because otherwise,
# you need to extract both children and NavigableStrings,
# and you can't extract NavigableStrings
# while looping over them because it affects the loop iterator.
def remove_all_children(tag):
    # Tried various ways of looping over em's children,
    # but neither of these iterators includes NavigableString
    # for c in tag.children:
    for c in tag.find_all(recursive=True):
        # Tried both extract and decompose:
        c.extract()
        # c.decompose()

    print("After removing children, tag =", tag)

    # Afterwards, we're left with NavigableStrings.
    for c in tag.contents:
        print("content:", c)
        # You can't extract them in a loop like this, because it affects
        # the iterator you're looping over:
        # c.extract()

    # But you can keep extracting the first one:
    while tag.contents:
        tag.contents[0].extract()

    print("After extracting contents, tag =", tag)

# A good test case for this:
ORIG_HTML = '''<em><a href="some_url">link text</a> (original <a href="orig_url">orig text</a>)</em>'''
soup = BeautifulSoup(ORIG_HTML, 'lxml')
em = soup.find('em')
remove_all_children(em)

# Wrap a container around an existing node
tag.wrap(soup.new_tag("b"))

# Replace a tag with another tag:
for b in soup.find_all('b'):
    b.name = 'strong'

# Delete an attribute but keep the tag:
del body["bgcolor"]
del body["style"]

# Join consecutive similar tags:
# see join_consecutive_tags() in losalamosmeetings.py.

# Change a title -- doesn't seem to be documented anywhere
if not soup.title.string:
    soup.title.string = "Document Title"

# Insert a tag at the beginning or end inside another tag:
from bs4 import NavigableString
b_tag = soup.new_tag("b")
soup.body.insert(0, b_tag)
btext = NavigableString("this is bold")
b_tag.append(btext)

# Insert a tag after another one:
article = soup.find('article')
new_tag = soup.new_tag("tagname")
new_tag.append("some text here")
# insert the new tag after the article
article.insert_after(new_tag)

# Add some style to an element or to the head:
para["class"] = "fileno"
head = soup.head
head.append(soup.new_tag('style', type='text/css'))
head.style.append('.someclass { background-color: #7fb; }')

# find elements by class:
mydivs = soup.find_all("div", {"class": "stylelistrow"})

# Look for the next p tag after the current tag:
tag.find_next('p')
tag.find_next_sibling('p')

# Find the next sibling after a tag:
tag.find_next_sibling()

# linkify according to a pattern (use a smarter pattern than this):
from bs4 import BeautifulSoup, NavigableString
LINK_PAT = re.compile('^https://')
def linkify(soup):
    for link in soup.body.findAll(string=LINK_PAT):
        if type(link) is not NavigableString:
            continue
        url = str(link)
        print("linkifying", url, file=sys.stderr)
        atag = soup.new_tag("a", href=url)
        atag.string = url
        link.replace_with(atag)


# Prettyprint output:
soup.prettify()

# SoupStrainer:
# a faster way to search through long/many html if you're only
# looking for a few things.

import bs4
from urllib.request import urlopen as request
from bs4 import BeautifulSoup as soup
from bs4 import SoupStrainer as strainer

url = 'https://www.newegg.com/p/pl?d=graphics+cards'

# opening connection, grabbing the HTML from the page
client = request(url)
page_html = client.read()
client.close()

only_item_cells = strainer("div", attrs={"class": "item-cell"})
page_soup = soup(page_html, 'html.parser', parse_only=only_item_cells)
page_soup_list = list(page_soup)

# Some other examples:
parse = BeautifulSoup(req.content, 'html.parser',
                      parse_only=SoupStrainer('meta'))
for link in parse:
    ...

tagsWithClass = SoupStrainer('p',{'class': 'refpurpose'})
soup = BeautifulSoup(siteData, "lxml",  parse_only=tagsWithClass)

self._strainer = SoupStrainer('div', attrs={'class': [
    're_gall_top_1',    # 제목, 글쓴이, 작성시각
    'btn_recommend',    # 추천, 비추천
    'gallery_re_title',  # 댓글
    's_write',          # 본문
]})

links = SoupStrainer('table', {'id': table_id})


# More:
# https://medium.com/codex/using-beautiful-soups-soupstrainer-to-save-time-and-memory-when-web-scraping-ea1dbd2e886f


########################################################
# JSON
########################################################

# Ways around "Object of type datetime is not JSON serializable"

# Easy quick fix: convert anything unknown to str
json.dumps(my_dictionary, indent=4, sort_keys=True, default=str)

# Better control: convert only what you want converted
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

json.dumps(yourobj, default=json_serial)

# Another way: subclass json.JSONEncoder
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)

json.dumps(yourobj, cls=DateTimeEncoder)

########################################################
# Networking and Requests
########################################################

# Basic requests use
r = requests.get(url)
# Now you have r.status_code, r.text, r.content (bytes),
# r.json(), json.loads(r.text)

# To handle cookies with requests, ignore the Requests documentation
# that says to use a RequestCookieJar: that's apparently only for
# setting cookies, not fetching them. Instead, use a Session:
session = requests.Session()
r = session.get(url)

# r.text (string), r.content (bytes), or r.json()

# r.encoding comes from the server,
# r.apparent_encoding is guessed from the text
# (either one may be None).

# The default timeout is None. Give it a timeout in seconds:
requests.get(url, timeout=5)
'''Note:

timeout is not a time limit on the entire response download; rather, an exception is raised if the server has not issued a response for timeout seconds (more precisely, if no bytes have been received on the underlying socket for timeout seconds).'''
# https://linuxpip.org/python-requests-timeout/
# You can specify a 2-tuple timeout=(3.05, 27)
# to set the connect and read timeouts separately.
# If you specify a single int, it will apply to both connect and read.


########################################################
# Enum and similar
########################################################

# Enum Howto: https://docs.python.org/3.10/howto/enum.html

>>> from enum import Enum
>>> class Weekday(Enum):
...     MONDAY = 1
...     TUESDAY = 2
...     WEDNESDAY = 3
...     THURSDAY = 4
...     FRIDAY = 5
...     SATURDAY = 6
...     SUNDAY = 7
...     #
...     @classmethod
...     def from_date(cls, date):
...         return cls(date.isoweekday())

>>> Weekday(3)
Weekday.WEDNESDAY

>>> print(Weekday.THURSDAY)
THURSDAY

>>> type(Weekday.MONDAY)
<enum 'Weekday'>
>>> isinstance(Weekday.FRIDAY, Weekday)
True

>>> print(Weekday.TUESDAY.name)
TUESDAY
>>> Weekday.WEDNESDAY.value
3

# Now we can find out what today is! Observe:

>>> from datetime import date
>>> Weekday.from_date(date.today())
Weekday.TUESDAY


# Named tuples

>>> from collections import namedtuple

>>> Point = namedtuple('Point', ['x', 'y'])
>>> p = Point(11, y=22)     # instantiate with positional or keyword arguments
>>> p[0] + p[1]             # indexable like the plain tuple (11, 22)
33
>>> x, y = p                # unpack like a regular tuple
>>> x, y
(11, 22)
>>> p.x + p.y               # fields also accessible by name
33
>>> p                       # readable __repr__ with a name=value style
Point(x=11, y=22)


###########################################################
# Properties
###########################################################

# See angle-properties.py
# which shows both property getters/setters, and operator overloading.

########################################################
# Some handy utility classes
########################################################

# Copying and moving files: shutil.copy and shutil.move

# Handle quoting for something that might need to be passed to a shell:
# in Python 3, shlex.quote() does it, but if it needs to be compatible
# with both 2 and 3, use pipes.quote().
# shlex also has split() and join(), e.g.
>>> html_index_links = 'div class="layout-homepage__lite"'
>>> shlex.split(html_index_links)
['div', 'class=layout-homepage__lite']



########################################################
# Sanitize a filename
########################################################
def sanitize_filename(badstr):
    return ''.join([x for x in badstr if x.isalpha() or x.isdigit()
                    or x in '-_.'])

###########################################################
# CGI: how to tell if something is run as a CGI or locally
###########################################################

if 'REQUEST_METHOD' in os.environ:
    print("Run as CGI", file=sys.stderr)
    form = cgi.FieldStorage()
else:
    print("Run locally")

# The CGI script is in os.getcwd()
os.getcwd()

# Current URL
url = os.environ["REQUEST_URI"]


###########################################################
# else in loops, e.g. "for..else"
###########################################################

"""
Why I'm always confused by "else" clauses and they never
seem to do what I want:

> else clauses have almost exactly opposite effects.
>
> while...else...
>
> executes the else if the body of the loop does NOT get executed.
>
> for...else...
>
> executes the else iff ALL iterations of the for loop DO complete.
>
>         -- Alan Gauld via Python-list

MRAB disagrees:
> In both cases, it executes the 'else' part if it didn't break out of the loop.
> That's it.
>
> If all of the iterations completed, then there was no break, so the 'else'
> part is executed.
>
> If there were no iterations, then there was no break, so the 'else' part is
> executed.
>
> It's the same for both of them.

Some people on python-list suggest it should have been named nobreak.

In a later discussion, Chris Angelico says:
> a for-else without a break is quite useless.
>
> The else is associated with the break to the exact extent that one is
>essential to the other's value.

In a later post, he adds that this is the typical use:
while True:     # or terating over things to search for
    if search(something): break
else:
    complain()


"""


########################################################
# unittest
########################################################

# Assuming a test/ subdirectory in the module toplevel:

# Run all tests:
# python3 -m unittest discover
# This will run from the top level, so imports will be relative to there.

# Run one test file
# python -m unittest test.test_epubtags

# Run one test in one class in one file:
# python -m unittest test.test_epubtags.TestEpubTags.test_epubtags

# Compare the contents of two files, giving errors for non-matching lines:
self.assertListEqual(list(open(test_path)),
                     list(open(reference_path)))

# approximate tests
def assertCloseEnough(a, b, tolerance=1e-5):
    """Assert if two values aren't close enough within a tolerance.
       Can accept two scalars or two iterables.
    """
    if hasattr(a, "__getitem__") and hasattr(b, "__getitem__"):
        if len(a) != len(b):
            raise AssertionError('Different lengths, %d vs %d'
                                 % (len(a), len(b)))
        for i, (aval, bval) in enumerate(zip(a, b)):
            if not math.isclose(aval, bval, rel_tol=tolerance):
                raise AssertionError("%dth elements differ: %f != %f"
                                     % (i, aval, bval))
        return

    if not math.isclose(a, b, rel_tol=tolerance):
        raise AssertionError('%f not close enough to %f' % (a, b))



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
# Fun with generators
########################################################
# See http://www.dabeaz.com/generators/

# "yield from" to delegate iteration:
def countdown(n):
    while n > 0:
        yield n
        n -= 1
def countup(stop):
    n = 1
    while n < stop:
        yield n
        n += 1
def up_and_down(n):
    yield from countup(n)
    yield from countdown(n)

# Generator expressions like list comprehensions
with open("access-log") as wwwlog:
    bytecolumn = (line.rsplit(None,1)[1] for line in wwwlog)
    bytes_sent = (int(x) for x in bytecolumn if x != '-')
    print("Total", sum(bytes_sent))

# "yield from":
#     yield from iterable
# is equivalent to:
#     for item in iterable:
#         yield item
# but is more efficient.

########################################################
# Lambda foo
########################################################

#
# Lambda in a loop needs intermediate variables
# (this comes up especially in TkInter programs, like populating menus)
# https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result
#
fcns = []
for i in range(5):
    fcns.append(lambda: print(i))
for f in fcns:
    f()    # prints 4 five times
# Instead, you need to make a lambda with its own intermediate variable:
fcns = []
for i in range(5):
    fcns.append(lambda x=i: print(x))
for f in fcns:
    f()    # prints 0 1 2 3 4

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
# sorting + lambda key examples
#
# NOTE: max and min can also use key functions
#
# The cmp function is obsolete in py3. Instead, use a key function,
# which is called on each element of the list prior to sorting,
# and for each item, returns something that can be simply sorted,
# like a string or int.
# https://wiki.python.org/moin/HowTo/Sorting
# The advantage of a key function is that a comparison function needs
# to be called on every comparison, a key function only once.
#
def sort_by_last_letter(words):
    # sorted() returns a new sorted list.
    print sorted(words, key = lambda a: a[-1])

    # list.sort() modifies the list in place
    words.sort(key = lambda a: a[-1])
    print words

# Speaking of sorting, insert into a list sorted with:
import bisect
bisect.insort(thelist, newstr)

#
# Iterate over two lists in parallel
#
for f, b in zip(foo, bar):
    print(f, b)

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

# See also this nifty use of map/reduce to redefine | to act
# like a shell data pipeline:
# https://code.activestate.com/recipes/580625-collection-pipeline-in-python/

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


# This overrides Qt's silly trapping of Ctrl-C,
# so you don't have to Ctrl-\ and get a core dump every time.
# Just trapping KeyboardInterrupt doesn't do it.
from PyQt5 import QtCore, QtGui, QtWidgets
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


################################################################
# varargs and asterisks in function signatures
################################################################

# https://www.srcecde.me/posts/2024/02/asterisk-and-forward-slash-as-function-parameters-python/

# collect additional positional arguments as a tuple
def asterisk_arg_func(first_argument, *additional_args):
    pass

# collect additional keyword arguments as a dictionary
def my_function(**kwargs):
    print(kwargs)

# Standalone * to specify Keyword-Only Parameters
# parameters defined after * are keyword-only
def my_function(a, b, *, c, d):
    print(a, b, c, d)
my_function(1, 2, c=3, d=4) # Valid
my_function(a=1, b=2, c=3, d=4) # Valid
my_function(1, 2, 3, 4) # TypeError

# / to specify Position-Only Parameters
# parameters defined before it (/) are position-only
def my_function(a, b, /, c, d):
    print(a, b, c, d)Z
my_function(1, 2, 3, d=4) # Valid
my_function(a=1, b=2, c=3, d=4) # TypeError

# * and \ both in function signature
def my_function(a, /, b, *, c):
    print(a, b, c)

my_function(1, b=2, c=3) # Valid
my_function(1, 2, c=3) # Valid
my_function(a=1, b=2, c=3) # TypeError: my_function() got some positional-only arguments passed as keyword arguments: 'a'

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
# Closures
################################################################

'''
From Fluent Python: a closure is function that retains the bindings
of the free variables that exist when the function is defined.

So it can remember variables from the enclosing function without
needing to rely on globals or object members.
'''

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

'''
<nedbat> If a string has only one reference, += modifies the string in place: O(1).  If the string has other references (r = s), it has to be copied first: O(N) <https://t.co/5pmUI4F4QQ> [@nedbat: Python’s string += is optimized to be fast when it can be, but it’s easy to get the slow (quadratic) behavior, so be careful:

<nedbat> import time

<nedbat> s = ""
<nedbat> for i in range(2_000_000):
<nedbat>     s += "x"
<nedbat>     # r = s      # do this to go slow.
<nedbat>     if i % 20_000 == 0:
<nedbat>         print(time.time())]
'''


################################################################
# Math
################################################################

# smallest, largest floats
sys.float_info.min
sys.float_info.max


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

# If you have a float representing degrees, do this:
>>> ephem.degrees(90. * ephem.pi / 180.)
1.5707963267948966

>>> seven_hours_from_radians = ephem.hours(7 * math.pi / 12)
>>> print(seven_hours_from_radians)
7:00:00.00
>>> float(seven_hours_from_radians) * 12 / math.pi
7.0


################################################################
# Matplotlib tips
################################################################

#
# To create interactive browser/javascript plots, 2 options:
# mpld3 is very powerful, but has to come from pip (the Debian
# version doesn't work and Ubuntu doesn't even have it);
# pygal is more available, possibly less powerful but very simple.
#

ax1 = fig.add_subplot(2, 1, 1)   # nrows, ncols, plotnum

#
# Multiple plots spaced out properly so titles don't draw over xlabels:
#
fig, axes = plt.subplots(nrows=numplots, ncols=1,
                         figsize=(8, 3.5 * numplots))
                         # figsize is  width, height in inches

axes[0].plot(distances, elevations, label="GPS elevation data", color="blue")
axes[0].set_xlabel("miles")
axes[0].set_ylabel("feet")
axes[0].grid(True)
axes[0].legend()
axes[0].title.set_text("Elevation Profile")

axes[1].plot(time, temperature, label="Temperature", color="red")
axes[1].set_xlabel("time")
axes[1].set_ylabel("temperature")
axes[1].grid(True)
axes[1].legend()
axes[1].title.set_text("Temperature Data")

plt.gcf().canvas.set_window_title("Elevation and temperature plots")
fig.tight_layout()        # "plt.tight_layout()" is equivalent
plt.show()


#
# Trimming all the spurious whitespace:
#

# Trim whitespace within each plot:
ax.set_xlim([0, enddate])
ax.set_ylim([0, data[-1]])

# Get the axis limits in data coordinates:
ax.get_xlim()

# Get axis limits in datetime:
# matplotlib are like ordinals except that they're floating point
# and datetime.datetime.fromordinal() will only accept ints.
import matplotlib.dates as mdates
[ mdates.num2date(x) for x in ax.get_xlim()) ]

# Trim whitespace between plots:
# pad controls padding around the top, bottom and sides of the page;
# w_pad controls space between plots horizontally (if columns > 1),
# h_pad controls space between plots vertically (if rows > 1).
plt.tight_layout(pad=2.0, w_pad=10.0, h_pad=3.0)

# There are lots and lots of other things that are supposed to
# eliminate whitespace; most of them don't work, and some of them,
# like ax.axis('tight') or plt.axis('tight'), prevent set_?lib
# and tight_layout from working.

# Exit on key q (this now seems to happen automatically, hooray)
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
# fig.autofmt_xdate()

# Two ways to do axis rotation:
plt.xticks(rotation=45, ha="right")
ax.tick_params(which='major', length=10, labelrotation=45, color='b')

#
# Custom ticks and labels for dates: see mpl_smart_dates.py.
#

################################################################
# Pandas
################################################################

# So far, Pandas is the worst documented, most difficult Python
# package I've seen so far.
# But if I ever manage to get it doing anything useful,
# I'll put that here.

# number of rows and columns:
df.shape

# View a specific row of a dataframe. Accepts slices, or : to include all.
# https://realpython.com/pandas-dataframe/#accessing-and-modifying-data
df.loc[11]

# print an entire dataframe, or column or whatever, without truncation.
# OPTION 1:
print(df.to_string())    # not recommended for huge datasets

# Extract every other row: use iloc
alt_rows = df.iloc[::2]

# OPTION 2:
with pd.option_context('display.max_rows', None,
                       'display.max_columns', None,
                       'display.precision', 3):
    print(df)

# OPTION 3:
# Permanently changes the pandas settings
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', -1)

# All dataframes hereafter reflect these changes.
display(df)

print('**RESET_OPTIONS**')

# Resets the options
pd.reset_option('all')

# OPTION 4: requires dependency 'tabulate'
print(df.to_markdown())


# Plot a time series of some random subset of a dataframe.
# I don't know why it doesn't plot the whole df,
# or how to get it to do that.
df.plot(x='datetime', y='temp0')

# Iterate over a dataframe:
>>> for row_label, row in df.iterrows():
...     print(row_label, row, sep='\n', end='\n\n')
...

>>> for col_label, col in df.iteritems():
...     print(col_label, col, sep='\n', end='\n\n')
...

>>> for row in df.loc[:, ['name', 'city', 'total']].itertuples():
...     print(row)
...

################################################################
# properties: lazy evaluation for a member variable
# instead of getters and setters
################################################################

class Temperature:
    def __init__(self, temperature=0):
        self.tempC = temperature
    def get_celcius(self):
        return self.tempC
    def set_celcius(self, tc):
        self.tempC = tc
    def get_fahrenheit(self):
        return (self.tempC * 1.8) + 32
    def set_fahrenheit(self, tf):
        self.tempC = (tf - 32) / 1.8
    # creating property objects
    celcius = property(get_celcius, set_celcius)
    fahrenheit = property(get_fahrenheit, set_fahrenheit)

# Or you can use a decorator:
class Temp:
    def __init__(self, temperature=0):
        self._tempC = temperature
    @property
    def celcius(self):
       return self._tempC
    @celcius.setter
    def celcius(self, value):
        self._tempC = value
    @property
    def F(self):
       return (self._tempC * 1.8) + 32
    @F.setter
    def F(self, value):
        self._tempC = (value - 32) / 1.8

################################################################
# Initializing class objects
################################################################

"""
A derived class can call super().__init(self)
but for immutables like str/bytes, __init__ only one argument, self.
You can't pass the initial value because __init__ isn't able to
change the immutable value.
So use __new__, which returns the new object created
and is is called before __init__.
"""

# To derive from bytes at init time, use __new__
# but note that __new__ is a static function, so there's no self.
class BytesSubclass(bytes):
    def __new__(cls, other, arguments):
        bytesvalue = compute(other, arguments)
        ob = bytes.__new__(cls, bytesvalue)
        ob.some_other_att = compute_something_else(other, arguments)
        return ob

# Another __new__ example that also shows an interesting comprehension
class Reverse(str):
    def __new__(cls, sequence):
        return super().__new__(cls, sequence[::-1])

"""More notes:
Overriding __new__ is also the best way to implement a singleton.
"""

################################################################
# Inheriting from and supplementing a class
################################################################

## In File AAA.py: define aaa() and bbb().
## Now, to override just bbb() but keep the original aaa():

## File BBB.py

from AAA import *
import AAA

def bbb():
    print("This is BBB:bbb")


################################################################
# Walrus operator (3.8 and up)
################################################################

if (n := len(a)) > 10:
    print(f"List is too long ({n} elements, expected <= 10)")

# Loop over fixed length blocks
while (block := f.read(256)) != '':
    process(block)

[clean_name.title() for name in names
 if (clean_name := normalize('NFC', name)) in allowed_names]

################################################################
# Type hinting
################################################################

'''
Several ways of hinting about types in Python 3:
Type hinting with the typing module:
  https://docs.python.org/3/library/typing.html

def percent(num: float) -> int:

Function annotations, PEP 3107:
  https://www.python.org/dev/peps/pep-3107/

Some related tools:
MyPy: an experimental optional static type checker (uses type hints)
  http://mypy-lang.org/
PySonar: a type inferencer and indexer
  https://yinwang0.wordpress.com/2010/09/12/pysonar/
'''

################################################################
# Flask tips
################################################################
'''
Jinja put a comma after all but the last value:
{% if not loop.last %},{% endif %}
'''

################################################################
# pip tips
################################################################

'''
List all packages installed with pip:
    pip list -l
(that doesn't actually list everything, though)

Related but less helpful commands, which include system packages:
    pip list
includes the version of every package.
    pip freeze
doesn't include versions.
pip list includes a few more packages than pip freeze

    pip list --user
does something else, creating a very short but not very useful list.

pip show <packagename>
shows info about a package.

Pip reinstall:
    pip install -I
--force-reinstall isn't enough, you need --upgrade which is -I

Install a particular version:
pip install pytopo==1.7.3

There is no reliable way to upgrade all packages, a la apt upgrade.
Here are various hacks and partial solutions people have come up with.

List outdated packages:
pip list --outdated

Upgrade all packages:
Some people point to things like:
pip install $(pip list --outdated | tail -n +2 | awk '{ print $1 }') --upgrade
but that doesn't actually work.

Some other possibilities:
pip3 list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip3 install -U
pip3 list | awk '{print $1}' | xargs -n1 pip3 install -U

https://coderwall.com/p/quwaxa/update-all-installed-python-packages-with-pip
has some other suggestions.

Get a list of installed files:
Basically, you can't. pip show -f packagename
gives a Location which may or may not
be where every file in the package ends up.
pip uninstall packagename does give the full list, but there's no -n
option so you have to actually install the package to see the file list.
'''

################################################################
# Virtualenv/venv
################################################################

'''Python3
python3 -m venv ~/pythonenv/envname
python3 -m venv --system-site-packages ~/pythonenv/envname
  (requires python3-venv)
'''
'''Python2
virtualenv ~/pythonenv/envname
  (requires virtualenv and python-virtualenv)
'''

'''
Optionally, add --system-site-packages to either of these.

Then activate it:
source ~/pythonenv/envname/bin/activate
VIRTUAL_ENV_DISABLE_PROMPT=1 source $HOME/pythonenv/3env/bin/activate
'''

'''
Find out what's installed in a virtualenv:
pip list --local
pip freeze --local
The former is easier to read.
'''

'''
Upgrade everything in a venv -- but DON'T DO THIS WITH --system-packages,
it will try to pip upgrade all your system packages too!
pip install -U $(pip freeze | awk '{split($0, a, "=="); print a[1]}')

See also my pip_upgrade.py script.
'''

################################################################
# Building and packaging
################################################################

'''
packaging.python.org is the new authoritative resource.
Best tutorial I've found on Packaging Python Projects:
https://packaging.python.org/tutorials/packaging-projects/

Installing to a virtualenv (don't use setup.py install):
  pip install .

Developing a package in a virtualenv:
  pip install -e .
(OR
  python3 setup.py develop
but the pip option is preferred; calling setup.py won't properly tell
pip that it's installed. Read more:
https://stackoverflow.com/questions/30306099/pip-install-editable-vs-python-setup-py-develop
)

This makes links to the live sourcedir, so you will get changes automatically.

When finished, if you don't want the package there any more:
  setup.py develop --uninstall

Test installing in a virtualenv:

python3 -m venv /tmp/testpythonenv
source /tmp/testpythonenv/bin/activate

If building from the test env:
pip install wheel

If installing the current project into the test env:
pip install .

Test and make sure it works.

Save what's installed in the venv, with versions:
pip freeze > requirements.txt

Install from a requirements.txt:
pip install -r requirements.txt

Generate a dist:
python3 setup.py clean
python3 setup.py sdist bdist_wheel
    (should generate two files in dist/)

Upload to Test PyPI
  First disable keyring (only need once) if you don't use Kwallet:
    keyring disable
  per https://twine.readthedocs.io/en/latest/#disabling-keyring

Set VERSION to something like 1.2rc1
because you may need to change it several times when testing uploads.

twine upload --repository testpypi dist/*
  (older:
   python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
  )

Install and test in a new empty virtualenv:
if you used preN or rcn in the version number, be sure to include ==VERSION

pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple PACKAGENAME==VERSION

Ideally, also test on a separate default account on some distro like Ubuntu,
or on other OSes.

If that doesn't work (e.g. on Ubuntu eoan), try:
  pip install --index-url https://test.pypi.org/simple/ --no-deps PACKAGENAME
  https://bugs.launchpad.net/ubuntu/+source/python-pip/+bug/1833229
  The no-deps is because test pypi may not have all the same dependencies.
  But it means you can't test the dependencies in your 

If everything works, upload to the real PyPI:
twine upload dist/*

Specifying required versions:
install_requires = [ 'numpy>=1.17', ... ]

See also ZipApp, for distributing several files zipped together
into one runnable file:
https://docs.python.org/3/library/zipapp.html
See youtube-dl as an example.
You can unzip it with unzip, which will skip the shebang line
(but emacs gets confused by it).

Good way to generate requirements.txt if there's already a setup.py:
pip-compile
(Uses specific versions, so you may want to edit it afterward.)

Building and Uploading Sphinx docs:
Best ever: https://samnicholls.net/2016/06/15/how-to-sphinx-readthedocs/
but once it's set up, just update the project and it should build automatically
but check to make sure by logging in to: https://readthedocs.org/dashboard/

More official:
https://dont-be-afraid-to-commit.readthedocs.io/en/latest/documentation.html

This is from 2009 and is probably obsolete:
https://pythonhosted.org/an_example_pypi_project/buildanduploadsphinx.html

Possibly useful links:
https://www.tjelvarolsson.com/blog/begginers-guide-creating-clean-python-development-environments/
http://www.siafoo.net/article/77#install-vs-develop


https://realpython.com/python-concurrency/
https://realpython.com/python-lambda
https://realpython.com/documenting-python-code/#docstrings-background
'''

################################################################
# pdb, Python debugging
################################################################
# Debug on ctrl-C:

def debug_signal_handler(signal, frame):
    import pdb
    pdb.set_trace()
import signal
signal.signal(signal.SIGINT, debug_signal_handler)


################################################################
# New stuff in specific Python versions
################################################################

# https://nedbatchelder.com/blog/202105/whats_in_which_python_3739.html
# https://python.plainenglish.io/killer-features-by-python-version-c84ca12dba8?gi=ee54e7167a55
