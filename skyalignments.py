#!/usr/bin/env python3

import ephem
from datetime import datetime
import xml.dom.minidom
import math
import sys
from pprint import pprint


def find_rise_set(observer, body):
    start_time = observer.date
    observer.date = observer.previous_setting(body)
    body.compute(observer)
    setting = body.az
    observer.date = start_time
    observer.date = observer.next_rising(body)
    body.compute(observer)
    rising = body.az
    return { 'rise': rising / ephem.degree, 'set': setting / ephem.degree }


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


def angle_between(wp1, wp2):
    '''Bearing from one waypoint to another.
       Waypoints are [name, lat, lon, ele]
    '''
    # https://www.movable-type.co.uk/scripts/latlong.html
    # https://stackoverflow.com/questions/3932502/calculate-angle-between-two-latitude-longitude-points
    lat1, lon1 = wp1[1], wp1[2]
    lat2, lon2 = wp2[1], wp2[2]
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) \
        - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (360. - math.atan2(y, x) / ephem.degree) % 360


def find_alignments(observer, waypoints, year=None):
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

    # Now go through all the angles between waypoints and see if
    # any of them correspond to any of the astronomical angles.
    matches = []
    for wp1 in waypoints:
        for wp2 in waypoints:
            if wp1 == wp2:
                continue
            angle = angle_between(wp1, wp2)

            # Does that angle match any of our astronomical ones?
            for season in azimuths:
                for body in azimuths[season]:
                    for event in azimuths[season][body]:
                        if abs(azimuths[season][body][event] - angle) < DEGREESLOP:
                            matches.append([wp1[0], wp2[0],
                                            '%s %s%s' % (season, body, event)])

    print("Matches:")
    pprint(matches)


def read_track_file_GPX(filename):
    """Read a GPX track file. Ignore tracks.
       Return a list of [name, lat, lon, ele] floats for waypoints.
    """

    dom = xml.dom.minidom.parse(filename)
    first_segment_name = None

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
        if not name:
            pointno += 1
            name = "Point %d" % pointno

        waypoints.append([ name, lat, lon, ele ])

    pprint(waypoints)
    return waypoints


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


if __name__ == '__main__':
    filename = sys.argv[1]
    waypoints = read_track_file_GPX(filename)
    if not waypoints:
        print("No waypoints in", filename)
        sys.exit(1)

    print("First waypoint:", waypoints[0])
    observerPoint = waypoints[0]

    observer = ephem.Observer()
    # Observer will take degrees as a string, but if you pass it floats
    # it expects radians, though that's undocumented.
    observer.lat = observerPoint[1] * ephem.degree
    observer.lon = observerPoint[2] * ephem.degree
    if len(observerPoint) > 3:
        observer.elevation = observerPoint[3]
    else:
        observer.elevation = 500.0  # meters
    observer.name = "%s %f, %f, %f" % (observerPoint[0],
                                       observer.lon, observer.lat,
                                       observer.elevation)
    print(observer)
    print()

    find_alignments(observer, waypoints)
