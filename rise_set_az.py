#!/usr/bin/env python3

import ephem
from ephem import cities

import argparse
import datetime
import sys


# Slop allowed in phase calculation, in percent:
PHASESLOP = 5


def find_rise_set(observer, body, rise, start, end, targetaz, phase, slop):
    # convert angles to radians
    slop *= ephem.pi / 180
    targetaz *= ephem.pi / 180

    observer.date = start
    while observer.date < end:
        if rise:
            observer.date = observer.next_rising(body)
        else:
            observer.date = observer.next_setting(body)
        body.compute(observer)

        if phase > 0:
            if abs(body.phase - phase) > PHASESLOP:
                continue

        if abs(body.az - targetaz) < slop:
            print("%s: %.1f at %d%% illuminated" % (observer.date,
                                                    body.az * 180 / ephem.pi,
                                                    body.phase))


def observer_for_city(city):
    try:
        return ephem.city(city)
    except KeyError:
        pass

    try:
        return cities.lookup(city)
    except ValueError:
        pass

    # Add some cities pyephem doesn't know:
    if city == 'San Jose':     # San Jose, CA at Houge Park
        observer = ephem.Observer()
        observer.name = "San Jose"
        observer.lon = '-121:56.8'
        observer.lat = '37:15.55'
        observer.elevation = 100
        return observer

    elif city == 'Los Alamos':  # Los Alamos, NM Nature Center
        observer = ephem.Observer()
        observer.name = "Los Alamos"
        observer.lon = '-106:18.36'
        observer.lat = '35:53.09'
        observer.elevation = 2100
        return observer

    elif city == 'White Rock':  # White Rock, NM Visitor Center
        observer = ephem.Observer()
        observer.name = "White Rock"
        observer.lon = '-106:12.75'
        observer.lat = '35:49.61'
        observer.elevation = 1960
        return observer

    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Calculate sun/moon rise/set")

    parser.add_argument("--moon", dest="moon", default=False,
                        action="store_true", help="Moon (default)")
    parser.add_argument("--sun", dest="sun", default=False,
                        action="store_true", help="Sun (rather than moon)")

    parser.add_argument("-r", "--rise", dest="rise", default=False,
                        action="store_true", help="Rise (default)")
    parser.add_argument("-s", "--set", dest="set", default=False,
                        action="store_true", help="Set (rather than rise)")

    parser.add_argument("-a", "--azimuth", action="store",
                        dest="az", type=int,
                        help='Target rise/set azimuth, in decimal degrees')

    parser.add_argument("-p", "--phase", action="store", default=0,
                        dest="phase", type=int,
                        help='Phase percent (default: all phases)')

    parser.add_argument("-o", "--observer", action="store",
                        dest="observer", default="White Rock",
                        help='Observer location')

    parser.add_argument("--slop", action="store", dest="slop", default=1,
                        type=int,
                        help="Slop degrees allowed (default 2)")

    parser.add_argument("-S", "--start", dest="start", default=None,
                        help="Start date, YYYY-MM-DD, "
                             "default: today",
                        type=lambda s: datetime.datetime.strptime(s,
                                                                  '%Y-%m-%d'))
    parser.add_argument("-E", "--end", dest="end", default=None,
                        help="End date, YYYY-MM-DD, "
                             "default: end of start year",
                        type=lambda s: datetime.datetime.strptime(s,
                                                                  '%Y-%m-%d'))

    args = parser.parse_args(sys.argv[1:])

    observer = observer_for_city(args.observer)

    if args.sun:
        body = ephem.Sun()
    else:
        body = ephem.Moon()

    rise = not args.set
    if rise:
        print("Finding %srises" % body.name)
    else:
        print("Finding %ssets" % body.name)

    if not args.start:
        args.start = datetime.datetime.now()
    if not args.end:
        args.end = args.start.replace(month=12, day=31, hour=23)

    vals = find_rise_set(observer, body, rise,
                         ephem.Date(args.start), ephem.Date(args.end),
                         args.az, args.phase, args.slop)
