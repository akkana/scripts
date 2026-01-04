#! /usr/bin/env python3

#
# A test script that hangs on network requests, for testing
# client-side scripts.
#
# Usage: delaytest.cgi/?delay=d&count=c
#

import os, sys
import string
import time
import cgi

print("""Content-Type: text/html

<head>
<title>Network request tester</title>
</head>
<body>
<h1>Network request tester</h1>
<p>
Hello, world. Now we'll hang for a bit ...
""")
# These flushes unfortunately don't do anything to help things show up faster,
# at least if you're loading from firefox.
sys.stdout.flush()

form = cgi.FieldStorage()
# print("form:", form, "<p>\n")
if 'delay' in form :
    delay = float(form["delay"].value)
else :
    delay = 10
if 'count' in form :
    count = int(form["count"].value)
else :
    count = 5
print("Delay %d, count %d<br>" % (delay, count))
sys.stdout.flush()

for i in range(count) :
    time.sleep(delay)
    print("<p>\nAnother line %d" % i)
    sys.stdout.flush()
