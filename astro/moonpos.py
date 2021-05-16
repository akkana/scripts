#!/usr/bin/env python

# Predict when the moon (or another body) will be at a specified
# altitude and azimuth during a specified time window
# over the course of a year.
# For instance: figure out when you can take a photo of the full
# moon rising over Lick Observatory; or predict when the full
# moon shining in your skylight might keep you awake.

# Copyright 2015,2019 by Akkana Peck. Share and enjoy under the GPL v2 or later.

import ephem
import sys, os
import datetime

# Define your own observer parameters here:
observer = ephem.Observer()
observer.name = "White Rock"
observer.lon = '-106.22'
observer.lat = '35.82'
observer.horizon = ephem.degrees(7.*ephem.pi/180.)
observer.elevation = 1980  # meters, though the docs don't actually say

DEGREES = 180. / ephem.pi

def discont_range(start, end, max):
    """Return a discontinuous range.
    Like range(start, end) except that if start > end, will "loop around"
    e.g. discont_range(22, 2, 24) will return [22, 23, 0, 1].
    """
    start = start%max
    end = end%max
    if start <= end:
        return list(range(start, end))
    return list(range(start, max)) + list(range(0, end))

def time_zone_offset(ephemdate):
    """Get the timezone offset at a given ephem.date
    """
    # First get the time zone offset. We'll assume the offset
    # is the same all day. That might make us be off by an hour
    # on start and end times for a few hours twice a year.
    local_hour = ephem.localtime(ephemdate).hour
    gmt_hour = ephemdate.tuple()[3]
    return (gmt_hour - local_hour) % 24
    # print "tzoffset:", tzoffset, "=", gmt_hour, "-", local_hour

def when_at_position(body, observer, targetalt, targetaz,
                     starttime, endtime, startdate=None, numdays=0,
                     slop=2., minphase=0, maxphase=100):
    """When will body be at the alt-az position during the time window,
       in the year following the date of the observer passed in
       (which defaults to today's date.)
    Args:
        body (ephem.Body)        -- The celestial body to be calculated.
        observer(ephem.Observer) -- the observing position.
        targetalt (float)        -- Altitude in decimal degrees.
        targetaz (float)         -- Azimuth in decimal degrees.
        starttime(int)           -- Earliest hour of day to check, GMT,
                                    on 24-hour clock, e.g. 18 for 6pm.
        endtime(int)             -- Latest hour of day to check, GMT.
                                    Will be ignored if starttime is a string.
        startdate                -- start datetime (default today)
        numdays                  -- # days to calculate (default 1 year)
        slop (Optional)          -- How much slop to allow in the alt/az
                                    positions each way (float, decimal degrees).
        minphase (Optional, int) -- What phase are we interested in (% illum)
        maxphase (Optional, int) -- What phase are we interested in (% illum)
    Returns:
        List of [[date, alt, az, phase], ...]
    """
    """
    Examples:
    When will the moon transit at altitude 45 degrees and phase at least half,
    and be bright in my skylight during MST nighttime hours?
        when_at_position(ephem.Moon(), observer, 45., 180., 5, 12, 5, 75, 25)

    When will the full moon rise exactly due east?
        when_rise_set_at_position(ephem.Moon(), observer, 90., "rise", 5,
                                  100, 20)
    """

    # PyEphem triples are (year, month, day)
    if not startdate:
        start_triple = observer.date.triple()
    else:
        start_triple = (startdate.year, startdate.month, startdate.day)
    start_triple = (start_triple[0], start_triple[1], int(start_triple[2]))
    # Can't just change st[2], it's a tuple, not a list

    results = []

    # Fix the observer's starting date:
    if startdate:
        observer.date = ephem.Date(start_triple + (starttime, 0, 0))
    else:
        # If no date was specified, start a week ago:
        observer.date = ephem.now() - (ephem.hour * 24 * 7)

    # Find the end date, which is an ephem.date.
    if numdays:
        end_date = ephem.Date((start_triple[0], start_triple[1],
                               start_triple[2] + ephem.hour * numdays * 24,
                               starttime, 0, 0))
    else:
        end_date = ephem.Date((start_triple[0]+1, start_triple[1],
                               start_triple[2],
                               starttime, 0, 0))

    def in_window(body, observer):
        body.compute(observer)
        alt = body.alt * DEGREES
        az = body.az * DEGREES
        print(observer.date, az, body.phase)
        if alt >= targetalt - slop and alt <= targetalt + slop \
           and az >= targetaz - slop and az <= targetaz + slop:
            if (body.phase > minphase and body.phase < maxphase):
                # print "In window at", observer.date
                return (alt, az)
            # else:
            #     print "In window but not in phase at", observer.date
        # else:
        #     print "NOT in window at", observer.date
        return False

    # How many ephem.date ticks long is the window of time we're considering?
    if starttime < endtime:
        window_hours = endtime - starttime
    else:
        window_hours = starttime + 24 - endtime
    window_hours *= ephem.hour

    # For now, loop by half-hour chunks
    # Half an hour will tell us whether the moon is appearing at all:
    LARGE_GRANULARITY = ephem.hour / 2
    # but once we find an appearance, we'd like to know the times
    # with more precision:
    SMALL_GRANULARITY = ephem.minute * 5

    # For the main loop, start with the less precise times.
    granularity = LARGE_GRANULARITY

    minalt = 91
    maxalt = -1
    minaz = 361
    maxaz = -1

    while observer.date <= end_date:
        # At the beginning of each loop, observer.date is set to
        # the start hour on a new day -- except that it's start hour
        # in GMT, not localtime, so we have to correct for that.
        # We need to loop through to the endtime on the same day,
        # then set observer.date to the starttime on the next day
        # and continue.
        # print "Day loop:", observer.date
        start_date_today = observer.date

        # tzoffset is dependent on date, so get ot for this day.
        # XXX We might be off by a day in when we apply the tzoffset, though.
        tzoffset = time_zone_offset(observer.date)
        observer.date += ephem.hour * tzoffset

        appearance = None
        disappearance = None

        # When will we stop the inner loop?
        time_window_end = observer.date + window_hours
        while observer.date < time_window_end:
            altaz = in_window(body, observer)
            if altaz:
                alt, az = altaz
                if alt < minalt: minalt = alt
                if alt > maxalt: maxalt = alt
                if az < minaz: minaz = az
                if az > maxaz: maxaz = az
            # print "Inner loop:", observer.date
            if not appearance and altaz:
                # It appeared! But if we're still using large granularity,
                # switch to small for a more precise prediction:
                if granularity == LARGE_GRANULARITY:
                    observer.date -= granularity
                    granularity = SMALL_GRANULARITY
                else:
                    appearance = observer.date
            elif appearance and not disappearance and not altaz:
                disappearance = observer.date
                granularity = LARGE_GRANULARITY
                break    # out of the inner loop
            observer.date += granularity

        if appearance:              # it appeared sometime during the window
            if not disappearance:   # it was still visible at window's end
                disappearance = end_date

            # XXX Would be better to show results with the min-max span
            # rather than just the average of min and max alt and az.
            # print minalt, maxalt, minaz, maxaz
            results.append([appearance, disappearance,
                            (minalt + maxalt)/2., (minaz + maxaz)/2.,
                            body.phase])

        # Set to start time in GMT on the following day
        observer.date = start_date_today + (ephem.hour * 24)

    return results

def when_rise_set_at_position(body, observer, targetaz, rise_set,
                              startdate=None, slop=5., numdays=365,
                              minphase=0, maxphase=100):
    """When will body rise at the target azimuth
       in the year following the date of the observer passed in
       (which defaults to today's date.)
    Args:
        body (ephem.Body)        -- The celestial body to be calculated.
        observer(ephem.Observer) -- the observing position.
        targetaz (float)         -- Azimuth in decimal degrees.
        rise_set(string)         -- "rise" or "set"
        slop (Optional)          -- How much slop to allow in the alt/az
                                    positions each way (float, decimal degrees).
        startdate                -- start datetime (default: today)
        numdays                  -- # days to calculate (default 1 year)
        minphase (Optional, int) -- What phase are we interested in (% illum)
        maxphase (Optional, int) -- What phase are we interested in (% illum)
    Returns:
        List of [[date, alt, az, phase], ...]
    """
    if not startdate:
        start_triple = observer.date.triple()
    else:
        start_triple = (startdate.year, startdate.month, startdate.day)
    start_triple = (start_triple[0], start_triple[1], int(start_triple[2]))
    observer.date = ephem.Date((start_triple[0], start_triple[1],
                                start_triple[2], 0, 0, 0))
    if numdays:
        end_date = ephem.Date((start_triple[0], start_triple[1],
                               start_triple[2] + ephem.hour * numdays * 24,
                               0, 0, 0))
    else:
        end_date = ephem.Date((start_triple[0]+1, start_triple[1],
                               start_triple[2],
                               0, 0, 0))

    results = []

    while observer.date <= end_date:
        if rise_set == "rise":
            observer.date = observer.next_rising(body)
        else:
            observer.date = observer.next_setting(body)

        body.compute(observer)
        az = body.az * DEGREES
        if az >= targetaz - slop and az <= targetaz + slop:
            if (body.phase > minphase and body.phase < maxphase):
                results.append([observer.date, observer.horizon*DEGREES, az,
                                body.phase])

        # Push the date forward a little bit to make sure we get the
        # next rise/set, not this one again.
        observer.date += ephem.hour

    return results

def timerange_str(ephemdate1, ephemdate2):
    """Print a pretty time range in localtime for two ephem.date objects
    """
    # Convert to localtime datetime objects
    lt1 = ephem.localtime(ephemdate1)
    lt2 = ephem.localtime(ephemdate2)
    return "%s - %s" % (lt1.strftime("%Y-%m-%d %H:%M"), lt2.strftime("%H:%M"))

def Usage():
    progname = os.path.basename(sys.argv[0])
    print("""Predict when the moon will rise, set or be at a specific position.
Usage: %s [-f] alt az start_hour end_hour
       %s [-f] [rise|set] azimuth
       %s [date time]
If -f is specified, only full or nearly-full moons will be considered;
-p sets minimum percent illuminated, +p sets maximum.
-s YYYY-MM-DD starts from another date, not now.
-d days: number of days to calculate
-m months: number of months to calculate
Hours are specified in local time.
""" % (progname, progname, progname))
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
        Usage()
    args = sys.argv[1:]
    minphase = 0
    maxphase = 100
    phasestr = "moon"
    MIN_FULL = 90
    startdate = None
    days = 365
    while True:
        if args[0] == '-f':
            minphase = MIN_FULL
            phasestr = "full moon"
            args = args[1:]
        elif args[0] == '-p':
            minphase = int(args[1])
            phasestr = "moon with at least %d%% illuminated" % minphase
            args = args[2:]
        elif args[0] == '+p':
            maxphase = int(args[1])
            phasestr = "moon with at most %d%% illuminated" % maxphase
            args = args[2:]
        elif args[0] == '-s':
            startdate = datetime.datetime.strptime(args[1], '%Y-%m-%d')
            args = args[2:]
        elif args[0] == '-d':
            days = int(args[1])
            args = args[2:]
        elif args[0] == '-m':
            days = int(args[1]) * 31
            args = args[2:]
        else:
            break

    if minphase > 0:
        if minphase == MIN_FULL:
            phasestr = "full moon"
        else:
            if maxphase < 100:
                phasestr = "moon between %d%% and %d%% illuminated" % (minphase,
                                                                       maxphase)
            else:
                phasestr = "moon with at least %d%% illuminated" % minphase
    elif maxphase < 100:
        phasestr = "moon with at most %d%% illuminated" % maxphase

    if len(args) == 2:
        #
        # Predict rise/set times:
        #
        if args[0] == "rise" or args[0] == "set":
            try:
                az = float(args[1])
            except ValueError:
                print("Error: azimuth must be a number, not %s" % args[1])
                print()
                Usage()
            results = when_rise_set_at_position(ephem.Moon(), observer,
                                                az, args[0], startdate, days,
                                                5, minphase, maxphase)
            print("""The %s will %s at azimuth %.1f during the next year at these times:
""" % (phasestr, args[0], az))
            sys.exit(0)

        else:
            #
            # Predict the moon's position at a single given time:
            #
            try:
                # set observer.date so that the date passed in is
                # the correct localtime. For that we need the timezone.
                day = ephem.Date(datetime.datetime.strptime(args[0],
                                                            "%Y-%m-%d"))
                tzoffset = time_zone_offset(day)
                hour, minute = list(map(float, args[1].split(':')))
                trip = day.triple()
                observer.date = (trip[0], trip[1], trip[2],
                                 hour+tzoffset, minute, 0)

                body = ephem.Moon()
                body.compute(observer)
                az = body.az * DEGREES
                print("The %s is at %.1f alt, %.1f az at phase %.1f at %s" % \
                    (body.name, body.alt * DEGREES, body.az * DEGREES,
                     body.phase,
                     ephem.localtime(observer.date).strftime("%Y-%m-%d %H:%M")))
                sys.exit(0)
            except SystemError:
                Usage()

    elif len(args) == 4:
        #
        # Predict when the moon will be in a specific alt/az window:
        #
        try:
            alt = float(args[0])
            az = float(args[1])
        except ValueError:
            print("Error: alt/az must be numbers")
            print()
            Usage()
        try:
            start_hour = int(args[2])
            end_hour = int(args[3])
        except ValueError:
            print("Error: start/end times must be integers")
            print()
            Usage()
        results = when_at_position(ephem.Moon(), observer,
                                   alt, az, start_hour, end_hour,
                                   startdate, days,
                                   5, minphase, maxphase)
        if days:
            timerange = "%d days" % days
        else:
            timerange = "year"
        print("""The %s will be near %.1f, %.1f 
between %dh and %dh during the next %s at these times:
""" % (phasestr, alt, az, start_hour, end_hour, timerange))

        print("%26s  %5s  %5s  %s" % ("Date/time range", "Alt", "Az", "Phase"))
        for r in results:
            if len(r) > 4 and r[4]:
                phase = "%2d%% illuminated" % r[4]
            else:
                phase = 'x'

            # pargs = tuple(r[0:3] + [phase])
            print("%26s  %5.1f  %5.1f  %s" % (timerange_str(r[0], r[1]),
                                               r[2], r[3], phase))

    else:
        Usage()
