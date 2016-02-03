#! /usr/bin/env python

#
# A test script that hangs on network requests, for testing
# client-side scripts.
#
# Usage: delaytest.cgi/?delay=d&count=c
#

import os, sys, string, random
import time
import cgi

print """Content-Type: text/html

<head>
<title>Network request tester</title>
</head>
<body>
<h1>Network request tester</h1>
<p>
Hello, world. Now we'll hang for a bit ...
"""

form = cgi.FieldStorage()
# print "form:", form, "<p>\n"
if 'delay' in form :
    delay = int(form["delay"].value)
else :
    delay = 60
if 'count' in form :
    count = int(form["count"].value)
else :
    count = 300
print "Delay", delay, ", count", count, "<br>"

for i in range(count) :
    time.sleep(delay)
    print "<p>\nAnother line," i
