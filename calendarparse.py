#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Parse a text list of events in tabular format.
# Tries to be smart about the parsing, assuming the input data
# is coming from somebody who's pasting it from a word processor
# into some sort of dumb webmail page.
#
# Output either .ics iCalendar format or HTML list of events.
#
# TODO: detect times no matter where they are on a line.
# TODO: output HTML formatted like a calendar.

# Copyright 2016 by Akkana Peck: share and enjoy under the GPL v2 or later.

from icalendar import Calendar, Event

# You can stuff your data into this calstr, or read it from a file
# passed on the commandline.
calstr = '''  TITLE, FIRST LINE WILL BE IGNORED

2016	Jan 16	Board meeting, our city, 11 am – 3 pm

2016	Feb 3	Reception, 5:30-7:30 pm
                Hotel name?

2016	Feb 4	Group meeting.
                Where will we meet?

**** Lines that don't parse as dates/events will be ignored ****

2016	Mar 12 	Board meeting, our city, some location

2016	March 22	Deadline for Spring newsletter

'''

months = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
           "Sep", "Oct", "Nov", "Dec" ]

for line in calstr.split('\n'):
    if not line.startswith("20"):
        continue
    parts = line.split("\t")
    monthday = parts[1].split(" ")
    print "Split '" + parts[1] + "' to:", monthday
    month = None
    print "date is:", monthday
    for i, m in enumerate(months):
        if monthday[0].startswith(m):
            month = i + 1
            break
    if month == None:
        print "Couldn't parse month from", line
        continue
    day = int(monthday[1])
    print parts[0], month, day, ":", parts[2]

    cal = Calendar()
    cal['dtstart'] = '%4s%02d%02dT000000' % (parts[0], month, day)
    cal['summary'] = parts[2]
    print cal.to_ical()

