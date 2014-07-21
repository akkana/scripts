#! /usr/bin/env python

# Predict planetary visibility in the early evening (sunset to midnight),
# and upcoming conjunctions between two or more planets.
# Copyright 2014 Akkana Peck -- share and enjoy under the GPLv2 or later.

import ephem
import math

# How low can a planet be at sunset or midnight before it's not interesting?
min_alt = 10. * math.pi / 180.

# How close do two bodies have to be to consider it a conjunction?
max_conj = 3. * math.pi / 180.

sun = ephem.Sun()

planets = [
    ephem.Moon(),
    ephem.Mercury(),
    ephem.Venus(),
    ephem.Mars(),
    ephem.Jupiter(),
    ephem.Saturn()
    ]

planets_up = {}
for planet in planets:
    planets_up[planet.name] = None

observer = ephem.Observer()
observer.name = "Los Alamos"
observer.lon = '-106.2978'
observer.lat = '35.8911'
observer.elevation = 2286  # meters, though the docs don't actually say

oneday = ephem.hour * 24

# Loop from start date to end date,
# using a time of 10pm MST, which is 4am GMT the following day.
d = ephem.date('2014/7/19 04:00')
end_date = ephem.date('2017/1/1')
# end_date = ephem.date('2014/7/22')

def datestr(d):
    tup = d.tuple()
    return "%d/%d/%d" % (tup[1], tup[2], tup[0])

def sepstr(sep):
    deg = float(sep) * 180. / math.pi
    if deg < .5:
        return "less than a half a degree (%.2f)" % deg
    if deg < 1.:
        return "less than a degree (%.2f)" % deg
    return "%.2f" % deg

while d < end_date :
    #for planet in planets:
    #    planet.compute(observer)

    observer.date = d
    sunset = observer.previous_setting(sun)
    sunrise = observer.next_rising(sun)
    # print  "Sunset:", sunset, "  Sunrise:", sunrise

    visible_planets = []
    for planet in planets:
        # A planet is observable this evening (not morning)
        # if its altitude at sunset OR its altitude at midnight
        # is greater than a threshold, which we'll set at 10 degrees.
        observer.date = sunset
        planet.compute(observer)
        # print planet.name, "alt at sunset:", planet.alt
        if planet.alt > min_alt:
            if not planets_up[planet.name]:
                # print planet.name, "is up at sunset"
                planets_up[planet.name] = d;
            visible_planets.append(planet)

        else:
            # Try midnight
            # print "old date:", observer.date
            midnight = list(observer.date.tuple())
            midnight[3:6] = [7, 0, 0]
            observer.date = ephem.date(tuple(midnight))
            if observer.date < sunset:
                observer.date += oneday
            # print "new date:", observer.date
            planet.compute(observer)
            # print planet.name, "alt at midnight:", planet.alt
            if planet.alt > min_alt:
                if not planets_up[planet.name]:
                    print planet.name, "will rise before midnight"
                    planets_up[planet.name] = d;
                visible_planets.append(planet)
            else:
                # Planet is not up. Was it up yesterday?
                if planets_up[planet.name]:
                    print planet.name, "visible from", \
                        datestr(planets_up[planet.name]),\
                        "to", datestr(d)
                    planets_up[planet.name] = None

            # Go back to the sunset position, since that's the one
            # we'll use to compute separation.
            observer.date = sunset
            planet.compute(observer)

    # Done with computing visible_planets.
    # Now look for conjunctions, anything closer than 5 degrees.
    # XXX This will find conjunctions between two planets,
    # XXX but what about more? And we should the moon too.
    conjpairs = []
    if len(visible_planets) > 2:
        for p, planet in enumerate(visible_planets):
            for other in visible_planets[p+1:]:
                sep = ephem.separation(planet, other)
                if sep <= max_conj:
                    # print datestr(d), \
                    #     "Conjunction between", planet.name, "and", \
                    #     other.name, ", separation", sep
                    conjpairs.append((planet, other, sep))

    # Now combine conjunctions, e.g. (a, b) and (b, c) -> (a, b, c)
    conjunctions = []
    for pair in conjpairs:
        found = False
        for group in conjunctions:
            if pair[0] in group:
                group.append(pair[1])
                found = True
            elif pair[1] in group:
                group.append(pair[0])
                found = True
        if not found:
            conjunctions.append([pair[2], pair[0], pair[1]])
        elif pair[2] < group[0]:
            group[0] = pair[2]

    # if conjpairs:
    #     print d
    #     print conjpairs
    #     print conjunctions
    for c in conjunctions:
        print datestr(d), "Conjunction between", \
            ', '.join(p.name for p in c[1:]),
        if len(c) > 3:
            print "min separation",
        else:
            print "separation",
        print sepstr(c[0])

    # Add a day:
    d = ephem.date(d + oneday)

