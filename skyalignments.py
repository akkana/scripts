#!/usr/bin/env python3

import ephem
from datetime import datetime
import xml.dom.minidom
import math
import sys
from pprint import pprint
import argparse


def nearest_time(targettime, t1, t2):
    '''Given a target ephem.time and two other datetimes,
       return the time closer to the target.
    '''
    d1 = abs(targettime - t1)
    d2 = abs(targettime - t2)
    if d1 <= d2:
        return t1
    return t2


def find_rise_set(observer, obj, d=None):
    '''Given an object (like Sun or Moon), find its rising and setting time
       closest to the given date d, either preceding or following it,
       for the observer's location.
       If date isn't specified, use the observer's date.
    '''
    if d:
        observer.date = d
    prevrise = observer.previous_rising(obj)
    nextrise = observer.next_rising(obj)
    prevset = observer.previous_setting(obj)
    nextset = observer.next_setting(obj)

    riseset_ret = {}

    # Rise time
    observer.date = nearest_time(observer.date, prevrise, nextrise)
    obj.compute(observer)
    riseset_ret['rise'] = { 'az':   obj.az / ephem.degree,
                            'time': observer.date
                          }

    # Set time
    observer.date = nearest_time(observer.date, prevset, nextset)
    obj.compute(observer)
    riseset_ret['set'] = { 'az':   obj.az / ephem.degree,
                           'time': observer.date
                         }

    return riseset_ret


def find_azimuths(observer):
    riseset = {}

    # Find sunrise and sunset:
    riseset['sun'] = find_rise_set(observer, ephem.Sun())

    # Now find the full moon closest to the date,
    # which may be the next full moon or the previous one.
    lastfull = ephem.previous_full_moon(observer.date)
    nextfull = ephem.next_full_moon(observer.date)
    now = ephem.now()
    if now - lastfull > nextfull - now:
        observer.date = nextfull
    else:
        observer.date = lastfull

    riseset['full moon'] = find_rise_set(observer, ephem.Moon())

    return riseset


def bearing_to(wp1, wp2):
    # https://www.movable-type.co.uk/scripts/latlong.html
    # Don't trust any code you find for this: test it extensively;
    # most posted bearing finding code is bogus.
    # print("bearing from waypoints:", wp1, wp2)
    lat1, lon1 = math.radians(wp1[1]), math.radians(wp1[2])
    lat2, lon2 = math.radians(wp2[1]), math.radians(wp2[2])
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - \
        math.sin(lat1) * math.cos(lat2) * math.cos(lon2-lon1)

    return math.degrees(math.atan2(y, x)) % 360


def find_alignments(observer, waypoints, year=None, allpoints=False):
    '''Find all the alignments with solstice/equinox sun/moon rise/set.
       Returns a dict: { 'vernal equinox': { 'moon': { 'rise': 94.17... } } }
       of azimuth angles in decimal degrees
    '''
    azimuths = {}

    if not year:
        year = datetime.now().year
    start_date = ephem.Date('1/1/%d' % year)

    observer.date = ephem.next_equinox(start_date)
    azimuths['vernal equinox'] = find_azimuths(observer)

    observer.date = ephem.next_solstice(observer.date)
    azimuths['summer solstice'] = find_azimuths(observer)

    observer.date = ephem.next_equinox(observer.date)
    azimuths['autumnal equinox'] = find_azimuths(observer)

    observer.date = ephem.next_solstice(observer.date)
    azimuths['winter solstice'] = find_azimuths(observer)

    pprint(azimuths)

    # How many degrees is close enough?
    DEGREESLOP = 2.

    # If allpoints is set, check angles among all pairs of points.
    # Otherwise, only check angles from observer to other points.
    if allpoints:
        print("Looking for alignments among all points")
        observer_points = waypoints
    else:
        observer_points = [ [ observer.name,
                              observer.lat / ephem.degree,
                              observer.lon / ephem.degree,
                              observer.elevation ] ]

    # Now go through all the angles between waypoints and see if
    # any of them correspond to any of the astronomical angles.
    matches = []
    for wp1 in observer_points:
        print("\nChecking observer", wp1)
        for wp2 in waypoints:
            if wp1 == wp2:
                continue
            angle = bearing_to(wp1, wp2)
            print("  ... vs", wp2, angle)

            # Does that angle match any of our astronomical ones?
            for season in azimuths:  # vernal equinox, etc.
                for body in azimuths[season]:  # sun, full moon
                    for event in azimuths[season][body]:  # rise, set
                        event_az = azimuths[season][body][event]['az']
                        if abs(event_az - angle) < DEGREESLOP:
                            matches.append({
                                'observer': wp1[0],
                                'target':   wp2[0],
                                'event':    '%s %s%s' % (season, body, event),
                                'azimuth':  event_az,
                                'slop':     event_az - angle,
                                'time':     azimuths[season][body][event]['time'].datetime()
                            })

    return matches


def read_waypoint_file_CSV(filename):
    """Read a CSV waypoint file. Ignore tracks.
       Return a list of [name, lat, lon, ele] floats for waypoints.
    """
    import csv

    points = []
    observer = None
    with open(filename) as csvfp:
        reader = csv.DictReader(csvfp)
        for row in reader:
            # Each row is an OrderedDict
            try:
                if 'elevation' in row:
                    ele = float(row['elevation'])
                else:
                    ele = 0
                point = [ row['name'],
                          float(row['latitude']), float(row['latitude']),
                          ele ]
            except ValueError:
                print("ValueError on", row)
            if row['name'].lower() == "observer":
                observer = point
            else:
                points.append(point)

    return observer, points


def read_waypoint_file_GPX(filename):
    """Read a GPX waypoint file. Ignore tracks.
       Return a list of [name, lat, lon, ele] floats for waypoints.
    """

    dom = xml.dom.minidom.parse(filename)
    first_segment_name = None
    observer = None

    # Handle waypoints
    waypts = dom.getElementsByTagName("wpt")
    if not waypts:
        return []

    waypoints = []
    pointno = 0
    for pt in waypts:
        lat = float(pt.getAttribute("lat"))
        lon = float(pt.getAttribute("lon"))
        try:
            ele = float(get_DOM_text(pt, "ele"))
        except:
            ele = 500    # meters

        name = get_DOM_text(pt, "name")
        print("    { 'name': '%s', 'lat': %f, 'lon': %f }," % (name, lat, lon))
        if not name:
            pointno += 1
            name = "Point %d" % pointno

        if name.lower() == "observer":
            observer = [ 'Observer', lat, lon, ele ]
        else:
            waypoints.append([ name, lat, lon, ele ])

    # pprint(waypoints)
    return observer, waypoints


def get_DOM_text(node, childname=None):
    '''Get the text out of a DOM node.
       Or, if childname is specified, get the text out of a child
       node with node name childname.
    '''
    if childname:
        nodes = node.getElementsByTagName(childname)
        # print "node has", len(nodes), childname, "children"
        if not nodes:
            return None
        node = nodes[0]
    if not node:
        return None
    n = node.childNodes
    if len(n) >= 1 and n[0].nodeType == n[0].TEXT_NODE:
        return n[0].data
    return None


def save_alignments_as_GPX(alignments):
    '''Given a list of alignments [[observername, targetname, bearing, event]]
    '''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=""
        """Find alignments between latitude/longitude coordinate pairs
and the sun. moon, and other objects on special dates such as
solstices and equinoxes.

Observer location may be specified either with -o lat,lon,ele or by
naming one of the GPX waypoints 'Observer'; otherwise the first
waypoint in the first file will be taken as the observer location.

When specifying location on the command line, latitude and longitude
are in decimal degrees. Elevation is optional; it will be assumed to be
meters unless followed by the letter f,
e.g. -o 34.8086585,-103.2011914,1650f""",
                                     formatter_class=argparse.RawTextHelpFormatter)
    # Specify an observer:
    parser.add_argument('-o', '--observer', action="store", dest="observer",
                        help='Observer location (lat,lon[,ele])')

    # Specify an observer name:
    parser.add_argument('-n', '--observername', action="store",
                        dest="observername", help='Observer name')

    # Don't use an observer, check angles between all pairs of points:
    parser.add_argument('-a', "--all", dest="allpoints", default=False,
                        action="store_true",
                        help="Don't use an observer, check angles "
                              "between all pairs of points")

    parser.add_argument('waypointfiles', nargs='+',
                        help='GPX or CSV files containing waypoints')
    args = parser.parse_args(sys.argv[1:])

    if args.observer:
        floats = args.observer.split(',')
        lat = float(floats[0].strip())
        lon = float(floats[1].strip())
        if len(floats) > 2:
            if floats[2].endswith('f'):    # ends with f, convert feet to meters
                ele = float(floats[2][:-1].strip()) * 0.3048
            elif floats[2].endswith('m'):  # ends with m, already meters
                ele = float(floats[2][:-1].strip())
            else:                          # assume meters
                ele = float(floats[2].strip())
        else:
            ele = 0.
        observer_point = [ 'Observer', lat, lon, ele ]
    else:
        observer_point = None

    waypoints = []
    for filename in args.waypointfiles:
        if filename.lower().endswith('gpx'):
            obs, wp = read_waypoint_file_GPX(filename)
        elif filename.lower().endswith('csv'):
            obs, wp = read_waypoint_file_CSV(filename)
        else:
            print("Unknown file type %s: skipping" % filename)
            continue
        if wp:
            waypoints += wp
        else:
            print("No waypoints in", filename)
        if obs:
            observer_point = obs

    if not waypoints:
        parser.print_help()
        sys.exit(1)

    if not observer_point:
        print("Using first waypoint for observer:", waypoints[0])
        observer_point = waypoints[0]
        if not args.allpoints:
            waypoints = waypoints[1:]

    observer = ephem.Observer()
    # Observer will take degrees as a string, but if you pass it floats
    # it expects radians, though that's undocumented.
    observer.lat = observer_point[1] * ephem.degree
    observer.lon = observer_point[2] * ephem.degree
    if len(observer_point) > 3:
        observer.elevation = observer_point[3]
    else:
        observer.elevation = 500.0  # meters
    if args.observername:
        observer.name = args.observername
    else:
        observer.name = "%s %f, %f, %dm" % (observer_point[0],
                                            observer.lat / ephem.degree,
                                            observer.lon / ephem.degree,
                                            observer.elevation)
    print(observer)
    print()

    alignments = find_alignments(observer, waypoints, allpoints=args.allpoints)
    if alignments:
        print("\nFound Alignments from %s:" % observer.name)
        pprint(alignments)
        # save_alignments_as_GPX(alignments)

    else:
        print("Couldn't find any alignments with %s" % observer.name)

