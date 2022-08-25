#!/usr/bin/env python3

# https://gist.github.com/ParagDoke/2388d7311f11cab4fa5f5538fa694d0e

# The only examples are the tests:
# /usr/lib/python3/dist-packages/icalendar/tests/

import sys

from icalendar import Calendar
import datetime

import argparse


# Get the local timezone
localtz = datetime.datetime.now().astimezone().tzinfo


def read_ics_file(infile):
    """Parse an ics file into a dictionary.
    """
    cal = Calendar.from_ical(open(infile, 'rb').read())

    events = []

    for component in cal.walk():
        # The first component is the whole vcalendar, name 'VCALENDAR'
        if component.name != 'VEVENT':
            continue

        # if 'SUMMARY' in event:
        #     print("Yikes, more than one event!")
        event = {}

        event['SUMMARY'] = component.get('summary')
        event['DESCRIPTION'] = component.get('description')
        event['LOCATION'] = component.get('location')

        event['DTSTART'] = component.get('DTSTART').dt
        event['DTEND'] = component.get('DTEND').dt

        # I don't know what the dtstamp or exdate are. No docs.
        # dtstamp = component.get('DTSTAMP')
        # exdate = component.get('exdate')

        # Rewrite into current timezone
        event['LOCALSTART'] = event['DTSTART']
        # If it's a datetime.date, it can't do astimezone
        if hasattr(event['LOCALSTART'], 'astimezone'):
            event['LOCALSTART'] = event['LOCALSTART'].astimezone(localtz)
        event['LOCALEND'] = event['DTEND']
        if hasattr(event['LOCALEND'], 'astimezone'):
            event['LOCALEND'] = event['LOCALEND'].astimezone(localtz)
        # dtstamp.dt = dtstamp.dt.astimezone(localtz)

        events.append(event)

    return events


def print_event(event):
    """Print in an informal but readable way."""

    def print_if(key):
        if key in event and event[key]:
            # Description for some events is really long.
            print(key, "::", type(event[key]), event[key])
            if len(event[key]) > 200:
                # prevent TypeError: unhashable type: 'slice'
                print(f"{key}: {event[key][:200]} ...")
            else:
                print(f"{key}: {event[key]}")

    def difftimes(startend):
        """startend is either "START" or "END".
           Return the non-local time if it's different from localtime
           or is aware and in a different timezone,
           else None.
        """
        localkey = "LOCAL" + startend
        dtkey = "DT" + startend
        if dtkey not in event:
            return None
        if not hasattr(event[dtkey], 'hour'):
            # Just a date, not a datetime
            return None
        if hasattr(event[dtkey], 'tzinfo') and event[dtkey].tzinfo:
            # it's aware
            if event[dtkey].tzinfo != localtz:
                return event[dtkey]
            return None
        # Not aware
        if event[dtkey].hour != event[localkey].hour or \
           event[dtkey].minute != event[localkey].minute:
            return event[dtkey]
        return None

    print_if("SUMMARY")

    print(f"START: {event['LOCALSTART'].strftime('%a, %d %b %Y %I:%M %Z')}")
    dt = difftimes('START')
    if dt:
        print(f"      ({dt.strftime('%a, %d %b %Y %I:%M %Z')})")

    if event['LOCALEND'] != event['LOCALSTART']:
        print(f"  END: {event['LOCALEND'].strftime('%a, %d %b %Y %I:%M %Z')}")
        dt = difftimes('END')
        if dt:
            print(f"      ({dt.strftime('%a, %d %b %Y %I:%M %Z')})")

    print_if("LOCATION")
    print_if("DESCRIPTION")


def remind_for_event(ev):
    """Create a line that can be added to a file for /usr/bin/remind."""

    desc = ev['DESCRIPTION'].replace('\n\n', '\n').replace('\n', ' ||| ')
    print(f"REM {ev['LOCALSTART'].strftime('%d %m %Y')} +1 MSG {ev['SUMMARY']} ||| LOCATION {ev['LOCATION']} ||| DESCRIPTION: ||| {desc}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Parse ical files")
    parser.add_argument('-f', action="store", dest="format", default="text",
                        help='Output format: text (default), remind')
    parser.add_argument('files', nargs='+', help="Input ical files")
    args = parser.parse_args(sys.argv[1:])
    # print("args", args)

    all_events = []

    for f in args.files:
        all_events += read_ics_file(f)

    for ev in all_events:
        print()

        if args.format == "remind":
            remind_for_event(ev)

        else:
            print_event(ev)
