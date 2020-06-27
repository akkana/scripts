#!/usr/bin/env python3

# https://gist.github.com/ParagDoke/2388d7311f11cab4fa5f5538fa694d0e

# The only examples are the tests:
# /usr/lib/python3/dist-packages/icalendar/tests/

import sys

import pytz
from icalendar import Calendar
from pytz import timezone
from dateutil import rrule


def read_ics_file(infile):
    cal = Calendar.from_ical(open(infile, 'rb').read())

    try:
        localtz = timezone('America/Denver')
    except pytz.exceptions.UnknownTimeZoneError:
        sys.exit('Invalid timezone; unable to update ics file.')

    for component in cal.walk():
        if component.name == 'VEVENT':
            summary = component.get('summary')
            description = component.get('description')
            location = component.get('location')

            dtstart = component.get('DTSTART').dt
            dtend = component.get('DTEND').dt

            # I don't know what the dtstampor exdate are
            # dtstamp = component.get('DTSTAMP')
            # exdate = component.get('exdate')

            # Rewrite into current timezone
            localstart = dtstart.astimezone(localtz)
            localend = dtend.astimezone(localtz)
            # dtstamp.dt = dtstamp.dt.astimezone(localtz)

            print(f"START: {localstart.strftime('%a, %d %b %Y %I:%M %Z')}")
            if dtstart.tzinfo != localstart.tzinfo:
                print(f"      ({dtstart.strftime('%a, %d %b %Y %I:%M %Z')})")
            print(f"  END: {localend.strftime('%a, %d %b %Y %I:%M %Z')}")
            if dtend.tzinfo != localend.tzinfo:
                print(f"      ({dtend.strftime('%a, %d %b %Y %I:%M %Z')})")
            print("SUMMARY", summary)
            print("LOCATION", location)

            # Description for some events is really long.
            if len(description) > 300:
                print("DESCRIPTION", description[:300], "...")
            else:
                print("DESCRIPTION", description)

            # Recurring event?
            # All .ics files seem to have at least one RRULE line,
            # but it usually doesn't mean there's actually a recurrence.
            # A common pattern is
            # RRULE:FREQ=YEARLY;INTERVAL=1;BYDAY=1SU;BYMONTH=11
            # The icalendar module has no documentation except "look at
            # the examples", and none of the tests deals with finding
            # recurrence rules (there's test_recurrence.py, but it
            # seems to be oriented to a case that lists several dates
            # rather than a rule). Perhaps it can't handle them at all.
            if component.get('rrule'):
                print("*** THERE IS AN RRULE ***")
                reoccur = component.get('rrule').to_ical()
                for item in parse_recurrences(reoccur, startdt, exdate):
                    print("\n  RECURRENCE:")
                    print("    ITEM:", item)
                    print("    SUMMARY:", summary)
                    print("    DESCRIPTION:", description)
                    print("    LOCATION:", location)


#
# parse_recurrences is untested, copied from somewhere on the web.
# I'll test it the next time I see an ICS with a recurrence,
# if that ever happens.
#
def parse_recurrences(recur_rule, start, exclusions):
    """ Find all reoccuring events """
    rules = rrule.rruleset()
    first_rule = rrule.rrulestr(recur_rule, dtstart=start)
    rules.rrule(first_rule)
    if not isinstance(exclusions, list):
        exclusions = [exclusions]
        for xdate in exclusions:
            try:
                rules.exdate(xdate.dts[0].dt)
            except AttributeError:
                pass
    now = datetime.now(timezone.utc)
    this_year = now + timedelta(days=60)
    dates = []
    for rule in rules.between(now, this_year):
        dates.append(rule.strftime("%D %H:%M UTC "))
    return dates


if __name__ == '__main__':
    read_ics_file(sys.argv[1])
