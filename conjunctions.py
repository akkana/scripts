#! /usr/bin/env python

# Predict planetary visibility in the early evening (sunset to midnight),
# and upcoming conjunctions between two or more planets.
# Copyright 2014 Akkana Peck -- share and enjoy under the GPLv2 or later.

import ephem
import math

verbose = False
output_csv = True

# How low can a planet be at sunset or midnight before it's not interesting?
min_alt = 10. * math.pi / 180.

# How close do two bodies have to be to consider it a conjunction?
max_sep = 3.5 * math.pi / 180.

# How little percent illuminated do we need to consider something a crescent?
crescent_percent = 40

# Start and end times for seeing a crescent phase:
crescents = { "Mercury": [ None, None ], "Venus": [ None, None ] }

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

def datestr(d):
    tup = d.tuple()
    return "%d/%d/%d" % (tup[1], tup[2], tup[0])

def sepstr(sep):
    deg = float(sep) * 180. / math.pi
    # if deg < .5:
    #     return "less than a half a degree (%.2f)" % deg
    # if deg < 1.:
    #     return "less than a degree (%.2f)" % deg
    return "%.1f deg" % deg

class ConjunctionPair:
    '''A conjunction between a pair of objects'''
    def __init__(self, b1, b2, date, sep):
        self.bodies = [b1, b2]
        self.date = date
        self.sep = sep

    def __repr__(self):
        return "%s: %s and %s, sep %s" % (datestr(self.date), self.bodies[0],
                                          self.bodies[1], sepstr(self.sep))

    def __contains__(self, body):
        return body in self.bodies

class Conjunction:
    '''A collection of ConjunctionPairs which may encompass more
       than two bodies and several days.
       The list is not guaranteed to be in date (or any other) order.
    '''
    def __init__(self):
        self.bodies = []
        self.pairs = []

    def __contains__(self, body):
        return body in self.bodies

    def add(self, body1, body2, date, sep):
        self.pairs.append(ConjunctionPair(body1, body2, date, sep))
        if body1 not in self.bodies:
            self.bodies.append(body1)
        if body2 not in self.bodies:
            self.bodies.append(body2)

    def start_date(self):
        date = ephem.date('3000/1/1')
        for pair in self.pairs:
            if pair.date < date:
                date = pair.date
        return date

    def end_date(self):
        date = ephem.date('0001/1/1')
        for pair in self.pairs:
            if pair.date > date:
                date = pair.date
        return date

    def find_min_seps(self):
        return mindate, maxdate, minseps

    def andjoin(self, names):
        '''Join a list together like a, b, c and d'''
        if len(names) == 1:
            return names[0]
        elif len(names) < 4:
            return ', '.join(names[:-1]) + ' and ' + names[-1]

    def closeout(self):
        '''Time to figure out what we have and print it.'''

        # Find the list of minimum separations between each pair.
        startdate = ephem.date('3000/1/1')
        enddate = ephem.date('0001/1/1')
        minseps = []
        for i, b1 in enumerate(self.bodies):
            for b2 in self.bodies[i+1:]:
                minsep = 360  # degrees
                closest_date = None
                for pair in self.pairs:
                    if pair.date < startdate:
                        startdate = pair.date
                    if pair.date > enddate:
                        enddate = pair.date
                    if b1 in pair and b2 in pair:
                        if pair.sep < minsep:
                            minsep = pair.sep
                            closest_date = pair.date
                # Not all pairs will be represented. In a triple conjunction,
                # the two outer bodies may never get close enough to register
                # as a conjunction in their own right.
                if minsep < max_sep:
                    minseps.append((closest_date, minsep, b1, b2))
        minseps.sort()

        if output_csv:
            s = '"Conjunction of ' + self.andjoin(self.bodies) + '",'
            s += datestr(startdate) + "," + datestr(enddate) + ",,"
            s += "\""
            for m in minseps:
                s += " %s and %s will be closest on %s (%s)." % \
                     (m[2], m[3], datestr(m[0]), sepstr(m[1]))
            s += "\",,http://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Sachin_Nigam_-_starry_moon_%28by-sa%29.jpg/320px-Sachin_Nigam_-_starry_moon_%28by-sa%29.jpg,240,169,\"<a href='http://commons.wikimedia.org/wiki/File:Sachin_Nigam_-_starry_moon_%28by-sa%29.jpg'>starry moon on Wikimedia Commons</a>\""
            print s
        else:
            print "Conjunction of", self.andjoin(self.bodies),
            print "lasts from %s to %s." % (datestr(startdate), datestr(enddate))
            for m in minseps:
                print "  %s and %s are closest on %s (%s)." % \
                    (m[2], m[3], datestr(m[0]), sepstr(m[1]))

    def merge(self, conj):
        '''Merge in another Conjunction -- it must be that the two
           sets of pairs have bodies in common.
        '''
        for p in conj.pairs:
            self.pairs.append(p)
        for body in conj.bodies:
            if body not in self.bodies:
                self.bodies.append(body)

class ConjunctionList:
    '''A collection of Conjunctions -- no bodies should be shared
       between any of the conjunctions we contain.
    '''
    def __init__(self):
        self.clist = []

    def add(self, b1, b2, date, sep):
        for i, c in enumerate(self.clist):
            if b1 in c or b2 in c:
                c.add(b1, b2, date, sep)
                # But what if one of the bodies is already in one of our
                # other Conjunctions? In that case, we have to merge.
                for cc in self.clist[i+1:]:
                    if b1 in cc or b2 in cc:
                        c.merge(cc)
                        self.clist.delete(cc)
                return

        # It's new, so just add it
        c = Conjunction()
        c.add(b1, b2, date, sep)
        self.clist.append(c)

    def closeout(self):
        '''When we have a day with no conjunctions, check the list
           and close out any pending conjunctions.
        '''
        for c in self.clist:
            c.closeout()
        self.clist = []

oneday = ephem.hour * 24

web_image = {
    "Moon" : ("http://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Phase-088.jpg/240px-Phase-088.jpg", '''"<a href='http://commons.wikimedia.org/wiki/User:JayTanner/gallery'>Jay Tanner</a>"''', 240, 240),
    "Mercury" : ("../resources/astronomy/mercury.jpg", "", 240, 182),
    "Venus" : ("../resources/astronomy/venus.jpg", "", 240, 192),
    "Mars" : ("http://upload.wikimedia.org/wikipedia/commons/7/76/Mars_Hubble.jpg", "Hubble Space Telescope", 240, 240),
    "Jupiter" : ("http://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Jupiter.jpg/240px-Jupiter.jpg", '"USGS, JPL and NASA"', 240, 240),
    "Saturn" : ("http://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Saturn_%28planet%29_large.jpg/384px-Saturn_%28planet%29_large.jpg", "Voyager 2", 192, 240)
}

descriptions = {
    "Mars": "Mars is visible as a bright, reddish \"star\".",
    "Saturn": "Saturn is visible. A small telescope will show its rings.",
    "Jupiter": "Jupiter is visible. With binoculars you can see its four brightest moons."
    }

def quotecsv(s):
    if ',' in s or '"' in s:
        return '"' + s.replace('"', '""') + '"'
    return s

def finish_planet(p, d):
    if not planets_up[p]:
        return

    if p in descriptions.keys():
        if output_csv:
            isvis = quotecsv(descriptions[p])
        else:
            isvis = descriptions[p]
    elif p == "Venus" or p == "Mercury":
        isvis = p + " is visible in the early evening sky."
    else:
        isvis = p + " is visible."

    # How about crescent info?
    if p in crescents.keys():
        if crescents[p][0]:
            isvis += " A telescope will show a crescent from " \
                     + datestr(crescents[p][0])
            if crescents[p][1]:
                isvis += " to " + datestr(crescents[p][1])
        crescents[p] = [ None, None ]

    if output_csv:
        if p != 'Moon':
            if web_image[p]:
                img = web_image[p][0]
                cred = web_image[p][1]
                w = web_image[p][2]
                h = web_image[p][3]
            else:
                img = ""
                cred = ""
                w = ""
                h = ""

            print "%s,%s,%s,,%s,,%s,%s,%s,%s" % \
                (p, datestr(planets_up[p]), datestr(d), isvis,
                 img, w, h, cred)
    else:
        print datestr(planets_up[p]), "to", datestr(d), ":", isvis

    planets_up[p] = None

def run(start, end, observer, toolate):
    '''Find planetary visibility between dates start and end,
       for an observer whose location has been set,
       between sunset and "toolate" on each date, where toolate is a GMT hour,
       e.g. toolate=7 means we'll stop at 0700 GMT or midnight MDT.
    '''
    d = start
    conjunctions = ConjunctionList()

    if output_csv:
        print 'name,start,end,time,longname,URL,image,image width,image height,image credit'
    else:
        print "Looking for planetary events between %s and %s:\n" % \
            (datestr(d), datestr(end))

    def planet_is_up(planet, d):
        global crescents
        if not planets_up[planet.name]:
            planets_up[planet.name] = d;
        visible_planets.append(planet)

        if planet.name not in crescents.keys():
            return

        # Is it a crescent? Update its crescent dates.
        if planet.phase <= crescent_percent:   # It's a crescent now
            if not crescents[planet.name][0]:
                crescents[planet.name][0] = d
            else:
                crescents[planet.name][1] = d

    while d < end:
        observer.date = d
        sunset = observer.previous_setting(sun)
        # sunrise = observer.next_rising(sun)
        # print  "Sunset:", sunset, "  Sunrise:", sunrise

        midnight = list(observer.date.tuple())
        midnight[3:6] = [toolate, 0, 0]
        midnight = ephem.date(tuple(midnight))

        # We have two lists of planets: planets_up and visible_planets.
        # planets_up is a dictionary of the time we first saw each planet
        # in its current apparition. It's global, and used by finish_planet.
        # visible_planets is a list of planets currently visible.
        visible_planets = []
        for planet in planets:
            # A planet is observable this evening (not morning)
            # if its altitude at sunset OR its altitude at midnight
            # is greater than a threshold, which we'll set at 10 degrees.
            observer.date = sunset
            planet.compute(observer)
            # print planet.name, "alt at sunset:", planet.alt
            if planet.alt > min_alt:
                planet_is_up(planet, d)

            else:
                # Try midnight
                observer.date = midnight
                if observer.date < sunset:
                    observer.date += oneday
                planet.compute(observer)
                if planet.alt > min_alt:
                    planet_is_up(planet, d)

                # Planet is not up. Was it up yesterday?
                elif planets_up[planet.name]:
                    finish_planet(planet.name, d)

        # print datestr(d), "visible planets:", \
        #     ' '.join([p.name for p in visible_planets])
        # print "planets_up:", planets_up

        # Done with computing visible_planets.
        # Now look for conjunctions, anything closer than 5 degrees.
        # Split the difference, use a time halfway between sunset and midnight.
        saw_conjunction = False
        observer.date = ephem.date((sunset + midnight)/2)
        if len(visible_planets) > 1:
            for p, planet in enumerate(visible_planets):
                for planet2 in visible_planets[p+1:]:
                    sep = ephem.separation(planet, planet2)
                    if sep <= max_sep:
                        # print datestr(observer.date), planet.name, \
                        #     planet2.name, sepstr(sep)
                        conjunctions.add(planet.name, planet2.name,
                                         observer.date, sep)
                        saw_conjunction = True
        if not saw_conjunction:
            conjunctions.closeout()

        # Add a day:
        d = ephem.date(d + oneday)

    for p in visible_planets:
        finish_planet(p.name, d)

if __name__ == '__main__':
    output_csv = False

    # Loop from start date to end date,
    # using a time of 10pm MST, which is 4am GMT the following day.
    start = ephem.date('2014/8/15 04:00')
    # end = ephem.date('2017/1/1')
    end = ephem.date('2016/1/1')
    # For testing, this spans a Mars/Moon/Venus conjunction:
    # d = ephem.date('2015/2/10 04:00')
    # end = ephem.date('2015/3/10')

    observer = ephem.Observer()
    observer.name = "Los Alamos"
    observer.lon = '-106.2978'
    observer.lat = '35.8911'
    observer.elevation = 2286  # meters, though the docs don't actually say

    # What hour GMT corresponds to midnight here?
    # Note: we're not smart about time zones. This will calculate
    # a time based on the time zone offset right now, whether we're
    # currently in DST or not.
    # And for now we don't even calculate it, just hardwire it.
    midnight = 7

    try:
        run(start, end, observer, midnight)
    except KeyboardInterrupt:
        print "Interrupted"

