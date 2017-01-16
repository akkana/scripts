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
# TODO: output HTML formatted like a calendar, not a list of events.

# Copyright 2016 by Akkana Peck: share and enjoy under the GPL v2 or later.

from icalendar import Calendar, Event, vDatetime
import sys

months = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
           "Sep", "Oct", "Nov", "Dec" ]

def tabular_string_to_calendar(calstr):
    '''Parse an erratically formatted string.
       Return a list of icalendar.Calendar entries.
    '''
    entries = []
    for line in calstr.split('\n'):
        if not line.startswith("20"):
            continue
        parts = line.split("\t")
        monthday = parts[1].split(" ")
        # print "Split '" + parts[1] + "' to:", monthday
        month = None
        # print "date is:", monthday
        for i, m in enumerate(months):
            if monthday[0].startswith(m):
                month = i + 1
                break
        if month == None:
            print("Couldn't parse month from '%s'" % line)
            continue
        day = int(monthday[1])
        # print parts[0], month, day, ":", parts[2]

        cal = Calendar()
        cal['dtstart'] = '%4s%02d%02dT000000' % (parts[0], month, day)
        cal['summary'] = parts[2]

        entries.append(cal)

    return entries

def ics_file_as_html(filename):
    fp = open(filename)
    ics = fp.read().split('\n\n')
    fp.close()

    eventlist = []
    for event in ics:
        if not event:
            continue
        eventlist.append(Calendar.from_ical(event))

    return eventlist_as_html(eventlist)

def eventlist_as_html(entries):
    '''Take a list of icalendar.Calendar entries;
       format it as a list of events in HTML, returned as a string.
       Writes to icalendar format as an intermediary because that's
       the easiest way to get icalendar.Calendar to parse its date
    '''

    html = '''<table border=1 summary="This table shows the calendar of events. Each row is an event. Columns contain the event date, time, and description which includes the location">
<caption>Calendar of Events</caption>
<thead>
  <tr>
     <th id="date" width="15%">Date</th>
     <th id="time" width="10%">Time</th>
     <th id="description">Description and Place</th>
   </tr>
  </thead>
  <tbody>'''

    year = None

    for cal in entries:
        print("cal['DTSTART'] = %s" % cal['DTSTART'])
        # cal['DTSTART'] might be a icalendar.prop.vDDDTypes object
        # or it might be a string. Handle either type:
        try:
            starttime = cal['DTSTART'].dt
        except AttributeError:
            starttime = vDatetime.from_ical(cal['DTSTART'])

        if not year or starttime.year != year:
            year = starttime.year
            html += '''<tr>
          <td colspan="3"><h4>%d</h4></td>
        </tr>''' % year

        datestr = starttime.strftime("%A,<br />%B %d")
        timestr = ""

        html += '''<tr>
      <td headers="date">%s</td><td headers="time">%s</td>
      <td headers="description"><span class="alert">%s</td></tr>''' \
          % (datestr, timestr, cal['SUMMARY'])
        # Seems like it would be better to use
        # cal['SUMMARY'].encode('utf-8', 'xmlcharrefreplace'))
        # but python gives an error,
        # UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2
        # in position 43: ordinal not in range(128)

    html += '''</tbody>
</table>  <!-- calendar table -->'''

    return html

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(ics_file_as_html(sys.argv[1]))
        sys.exit(0)

    # You can stuff your data into this calstr, or read it from a file
    # passed on the commandline.
    # Note: the dash in the Jan 16 event is a nonascii character.
    # Leave it in place for testing, to make sure encode is called as needed.
    test_calstr = '''  TITLE, FIRST LINE WILL BE IGNORED

2016	Jan 16	Board meeting, our city, 11 am – 3 pm

2016	Feb 3	Reception, 5:30-7:30 pm
                Hotel name?

2016	Feb 4	Group meeting.
                Where will we meet?

**** Lines that don't parse as dates/events will be ignored ****

2016	Mar 12 	Board meeting, our city, some location

2016	March 22	Deadline for Spring newsletter

'''
    entries = tabular_string_to_calendar(test_calstr)

    for cal in entries:
        print(cal.to_ical())

    print(eventlist_as_html(entries))

