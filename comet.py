#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Look up a comet and compute its position, using Skyfield.
# This is a brand new function in Skyfield!
# https://rhodesmill.org/skyfield/kepler-orbits.html

from skyfield.api import Loader, Topos
from skyfield.data import mpc
from skyfield.constants import GM_SUN_Pitjeva_2005_km3_s2 as GM_SUN
from skyfield import almanac

import dateutil.parser
from datetime import timedelta

import argparse

import sys, os

load = Loader('~/.cache/skyfield')
with load.open(mpc.COMET_URL) as f:
    comets = mpc.load_comets_dataframe(f)

# Index by designation for fast lookup.
comets = comets.set_index('designation', drop=False)

ts = load.timescale(builtin=True)
eph = load('de421.bsp')
sun = eph['sun']
earth = eph['earth']

WHICH_TWILIGHT = "Nautical twilight"


def comet_by_name(namepat):
    # Exact search: row = comets.loc[cometname]

    # How to search for something containing a string in pandas:
    rows = comets[comets['designation'].str.contains(namepat)]

    # Found it!
    if len(rows) == 1:
        return rows.iloc[0]

    # No match
    if len(rows) == 0:
        return None

    # Multiple matches, so print them but return nothing.
    # pandas iterrows() returns two things but they're both the same object,
    # not an index and an object like you might expect. So ignore r.
    print("Matches from", len(comets), 'comets loaded:')

    for r, row in rows.iterrows():
        print(row['designation'])
    return None


def print_event_table(observer, cometvec, alm, t0, t1):
    """For debugging, Print a chromological table of all rise/set events.
       Harder to read but useful for debugging and guaranteed to
       be in chronological order.
    """
    t, y = almanac.find_discrete(t0, t1, alm)
    for ti, yi in zip(t, y):
        alt, az, distance = \
            observer.at(ti).observe(cometvec).apparent().altaz()
        t = ti.utc_datetime().astimezone()
        d = t.strftime("%Y-%m-%d")
        print("Rise" if yi else " Set", d, t.strftime("%H:%M %Z"),
              "%3d°%2d'" % az.dms()[:2])


def print_rises_sets(observer, cometvec, alm, t0, t1):
    """Print rises and sets in separate columns, easier to read."""
    t, y = almanac.find_discrete(t0, t1, alm)

    fmt = "%-10s    %-10s %-8s   %-10s %-8s   %-14s"
    print(fmt % ("Date", "Rise", "Azimuth", "Set", "Azimuth",
                 "Distance"))

    def reset_strings():
        nonlocal risetime, riseaz, settime, setaz, datestr
        risetime = ''
        riseaz = ''
        settime = ''
        setaz = ''
        datestr = ''

    reset_strings()

    for ti, yi in zip(t, y):
        alt, az, distance = \
            observer.at(ti).observe(cometvec).apparent().altaz()
        t = ti.utc_datetime().astimezone()
        newdatestr = t.strftime("%Y-%m-%d")

        if not datestr:
            datestr = newdatestr

        elif newdatestr != datestr and (risetime or settime):
            print(fmt % (datestr, risetime, riseaz, settime, setaz,
                         str(distance)))

            reset_strings()
            datestr = newdatestr

        if yi:
            risetime =  t.strftime("%H:%M %Z")
            riseaz = "%3d°%2d'" % az.dms()[:2]
        else:
            settime =  t.strftime("%H:%M %Z")
            setaz = "%3d°%2d'" % az.dms()[:2]

    # Print a line for the final date
    if risetime or settime:
        print(fmt % (datestr, risetime, riseaz, settime, setaz,
                     str(distance)))


def find_twilights(adate, alm_twilights):
    """Find twilight times at dawn and dusk on the given day.
       Return a skyvec Time.
    """

    # Convert to an aware datetime in the local timezone
    t0 = adate.utc_datetime().astimezone()

    # Start at midnight
    t0 = t0.replace(hour=0, minute=0, second=0, microsecond=0)
    t1 = t0 + timedelta(days=1)

    times, events = almanac.find_discrete(ts.utc(t0), ts.utc(t1),
                                              alm_twilights)

    twilights = []
    # Using Astronomical twilight makes sense, but maybe the
    # user wants to be a little more ambitious in searching
    for i, e in enumerate(events):
        if almanac.TWILIGHTS[e] == WHICH_TWILIGHT:
            twilights.append(times[i])

    return twilights


def svt2str(svt):
    """SkyView Time to string in local timezone"""
    return svt.utc_datetime().astimezone().strftime("%Y-%m-%d %H:%M %Z")


def print_alt_table(obstime, cometvec, obsvec, alm_twilights):
    """Print a table of the comet's alt and az for one day
       during darkness and astronomical twilight,
       and only when the comet is up.
    """
    dawn, dusk = [ t.utc_datetime().astimezone() for t in find_twilights(obstime, alm_twilights) ]
    t0 = obstime.utc_datetime().astimezone()
    # Start at midnight
    t0 = t0.replace(hour=0, minute=0, second=0, microsecond=0)
    curday = t0.day
    INCR = timedelta(minutes=15)
    night = True

    fmt= "%22s %10s %10s"
    print(fmt % ("Time", "Altitude", "Azimuth"))
    while t0.day == curday:
        # print("      Start loop:", t0.strftime("%Y-%m-%d %H:%M %Z"))
        if night and t0 > dawn and t0 < dusk:
            print(WHICH_TWILIGHT, "dawn")
            night = False
        elif not night and t0 >= dusk:
            print(WHICH_TWILIGHT, "dusk")
            night = True
        if night:
            t0t = ts.utc(t0)
            alt, az, distance = \
                obsvec.at(t0t).observe(cometvec).apparent().altaz()
            t0s = t0.strftime("%Y-%m-%d %H:%M %Z")
            if alt.degrees > 0:
                print(fmt % (t0s, "%3d°%2d'" % alt.dms()[:2],
                             "%3d°%2d'" % az.dms()[:2]))
        #     else:
        #         print(t0s, "too low")
        # else:
        #     print(t0.strftime("%Y-%m-%d %H:%M %Z"), "too bright")

        t0 += INCR


def calc_comet(comet_df, obstime, earthcoords, numdays=0, alt_table=False):
    # Generating a position.
    cometvec = sun + mpc.comet_orbit(comet_df, ts, GM_SUN)

    cometpos = earth.at(obstime).observe(cometvec)
    ra, dec, distance = cometpos.radec()
    print("RA", ra, "   DEC", dec, "   Distance", distance)

    if earthcoords:
        if len(earthcoords) > 2:
            elev = earthcoords[2]
        else:
            elev = 0
        obstopos = Topos(latitude_degrees=earthcoords[0],
                         longitude_degrees=earthcoords[1],
                         elevation_m=elev)
        print("\nObserver at",
               obstopos.latitude, "N  ", obstopos.longitude, "E  ",
              "Elevation", obstopos.elevation.m, "m")
        obsvec = earth + obstopos

        alt, az, distance = \
            obsvec.at(obstime).observe(cometvec).apparent().altaz()
        print("Altitude", alt, "     Azumuth", az, distance)

        alm_twilights = almanac.dark_twilight_day(eph, obstopos)
        dawn, dusk = find_twilights(obstime, alm_twilights)
        print(WHICH_TWILIGHT, ": Dawn", svt2str(dawn), "Dusk", svt2str(dusk))

        if numdays:
            print("\nRises and sets over", numdays, "days:")
            datetime1 = obstime.utc_datetime() - timedelta(hours=2)
            t0 = ts.utc(datetime1)
            t1 = ts.utc(datetime1 + timedelta(days=numdays))

            alm = almanac.risings_and_settings(eph, cometvec, obstopos)
            t, y = almanac.find_discrete(t0, t1, alm)

            print_rises_sets(obsvec, cometvec, alm, t0, t1)

        if alt_table:
            print()
            oneday = timedelta(days=1)
            while True:
                print_alt_table(obstime, cometvec, obsvec, alm_twilights)
                numdays -= 1
                if  numdays <= 0:
                    break
                # Add a day: there doesn't seem to be a way to do this
                # while staying within skyview's Time object.
                obstime = ts.utc(obstime.utc_datetime() + oneday)


def Usage():
    print(f"Usage: {os.path.basename(sys.argv[0])} comet-name [date]")
    print("  comet-name may be partial, e.g. '2020 F3'.")
    print("  date can be any format that dateutil.parser can handle.")
    sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Look up a comet and compute its position.")
    parser.add_argument('-t', action="store", dest="time",
                        help='Time (any format dateutil.parser handles)')
    parser.add_argument('-c', action="store", dest="coords",
                        nargs=2, type=float,
                        help="Observer's Latitude and longitude (degrees)")
    parser.add_argument('-e', action="store", dest="elev", type=float,
                        help="Observer's elevation (meters)")
    parser.add_argument('-d', action="store", dest="numdays",
                        type=int, default=0,
                        help="Number of days to show risings/settings")
    parser.add_argument('-a', "--alttable", dest="alttable", default=False,
                        action="store_true",
                        help="Print a table of altitudes "
                        "when the comet is visible")
    parser.add_argument("cometname",
                        help="Name (full or partial) of a comet")
    args = parser.parse_args(sys.argv[1:])
    # print(args)

    if args.time:
        pdate = dateutil.parser.parse(args.time)
        if not pdate.tzinfo:
            # interpret it locally by default
            pdate = pdate.astimezone()
        # skyfield Time seems to handle aware datetimes okay,
        # so even though this says utc it will handle the given tzinfo.
        t = ts.utc(pdate)
    else:
        t = ts.now()

    if args.coords and args.elev:
        args.coords.append(args.elev)

    comet_df = comet_by_name(args.cometname)

    if comet_df is not None:
        print(comet_df['designation'], "    ",
              t.utc_datetime().astimezone().strftime("%Y-%m-%d %H:%M %Z"))
        calc_comet(comet_df, t, args.coords, args.numdays, args.alttable)


