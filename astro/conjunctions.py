#! /usr/bin/env python

# Predict planetary visibility in the early evening (sunset to midnight),
# and upcoming conjunctions between two or more planets.
#
# Specifically written to generate the Sky page on the
# PEEC Nature Guides; so it's hardwired to Los Alamos coordinates
# and timezone, and the SQL format uses URLs for images that the
# PEEC sky page will use.
#
# Copyright 2014 Akkana Peck -- share and enjoy under the GPLv2 or later.

from __future__ import print_function

import ephem
import math

verbose = False

# How low can a planet be at sunset or midnight before it's not interesting?
# We'll half it for the moon.
min_alt = 10 * math.pi / 180.

# How close do two bodies have to be to consider it a conjunction?
max_sep = 3.5 * math.pi / 180.

# Half the moon's diameter, for checking occultations:
halfmoon = ephem.degrees('.25')

# How close does a bright planet need to be from the moon to be mentioned?
moon_sep = 25 * math.pi / 180.

# How little % illuminated do we need to consider an inner planet a crescent?
crescent_percent = 40

# Start and end times for seeing a crescent phase:
crescents = { "Mercury": [ None, None ], "Venus": [ None, None ] }

# What hour GMT corresponds to midnight here?
# Note: we're not smart about time zones. This will calculate
# a time based on the time zone offset right now, whether we're
# currently in DST or not.
# And for now we don't even calculate it, just hardwire it.
timezone = 7

sun = ephem.Sun()

planets = [
    ephem.Moon(),
    ephem.Mercury(),
    ephem.Venus(),
    ephem.Mars(),
    ephem.Jupiter(),
    ephem.Saturn()
    ]

planets_by_name = ["Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

planets_up = {}
for planet in planets:
    planets_up[planet.name] = None

saw_conjunction = False
visible_planets = []


def datestr(d):
    # The date may be wrong because of time zones. Convert to our timezone.
    lt = ephem.localtime(d)
    # return lt.strftime("%m/%d/%Y")
    return lt.strftime("%Y-%m-%d")


# For the web page, it's a little more friendly to say something like
# "will be closest on Mar 3" vs. "will be closest on 2017-03-03".
def friendlydate(d):
    lt = ephem.localtime(d)
    return lt.strftime("%b %d")


def sepstr(sep):
    deg = float(sep) * 180. / math.pi
    # if deg < .5:
    #     return "less than a half a degree (%.2f)" % deg
    # if deg < 1.:
    #     return "less than a degree (%.2f)" % deg
    return "%.1f deg" % deg


class ConjunctionPair:
    """A conjunction between a pair of objects"""
    def __init__(self, b1, b2, date, sep):
        self.bodies = [b1, b2]
        self.date = date
        self.sep = sep

    def __repr__(self):
        return "%s: %s and %s, sep %s" % (datestr(self.date), self.bodies[0],
                                          self.bodies[1], sepstr(self.sep))

    def __contains__(self, body):
        return body in self.bodies


def check_occultation(b1name, b2name, minsep, closest_date, observer):
    """Use a more fine-grained time step to check for a lunar occultation.
    """
    # Unfortunately, by the time we get here we only have a name,
    # not an ephem body. Get the body back:
    b1 = planets[planets_by_name.index(b1name)]
    b2 = planets[planets_by_name.index(b2name)]

    timestep = ephem.hour / 20

    # Go from a day earlier to a day later:
    enddate = closest_date + oneday
    observer.date = closest_date - oneday
    while observer.date < enddate:
        b1.compute(observer)
        b2.compute(observer)
        sep = ephem.separation(b1, b2)
        if sep < minsep:
            minsep = sep
            closest_date = observer.date
        observer.date += timestep

    return minsep, closest_date


class Conjunction:
    """A collection of ConjunctionPairs which may encompass more
       than two bodies and several days.
       The list is not guaranteed to be in date (or any other) order.
    """
    def __init__(self):
        self.bodies = []
        self.pairs = []

    def __contains__(self, body):
        return body in self.bodies

    def __repr__(self):
        return "Conjection: " + ', '.join(map(str, self.bodies))

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
        """Join a list together like a, b, c and d"""
        if len(names) == 1:
            return names[0]
        else:
            return ', '.join(names[:-1]) + ' and ' + names[-1]

    def closeout(self, observer):
        """Time to figure out what we have and print it."""

        if verbose:
            print("closeout", self.start_date(), "-", self.end_date())
            print("  bodies", self.bodies)
            print("  pairs", self.pairs)

        # Find the list of minimum separations between each pair.
        startdate = ephem.date('3000/1/1')
        enddate = ephem.date('0001/1/1')
        minseps = []
        moonclose = ephem.degrees('1')
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
                    # First check for lunar occultations.
                    if (b1 == 'Moon' or b2 == 'Moon') and minsep < moonclose:
                        minsep, closest_date = check_occultation(b1, b2, minsep,
                                                                 closest_date,
                                                                 observer)
                    minseps.append((closest_date, minsep, b1, b2))

        minseps.sort()

        def conjstr(b1, b2, sepdate, minsep):
            if b1 == 'Moon' and minsep < halfmoon:
                # It's probably an occultation.
                # Rather than try to predict the time,
                # just narrow it down to the nearest hour.
                sepdate_tuple = list(sepdate.tuple())
                hour = sepdate_tuple[3] - timezone
                if hour > sepdate_tuple[3]:
                    sepdate_tuple[2] -= 1
                sepdate_tuple[3] = hour
                if hour > 12:
                    hourstr = str(hour-12) + " pm"
                else:
                    hourstr = str(hour) + " am"

                seps = "POSSIBLE OCCULTATION around " + hourstr
            else:
                seps = sepstr(minsep)
            return " %s and %s will be closest on %s (%s)." % \
                     (b1, b2, friendlydate(sepdate), seps)

        if output_format == "csv":
            s = '"Conjunction of ' + self.andjoin(self.bodies) + '",'
            s += datestr(startdate) + "," + datestr(enddate) + ",,"
            s += "\""
            for m in minseps:
                s += conjstr(m[2], m[3], m[0], m[1])

            s += "\",,astronomy/starry_moon.jpg,240,169,\"<a href='http://commons.wikimedia.org/wiki/File:Sachin_Nigam_-_starry_moon_%28by-sa%29.jpg'>starry moon on Wikimedia Commons</a>\""
            print(s)

        elif output_format == "sql":
            s = "('Conjunction of " + self.andjoin(self.bodies) + "', "
            s += "'astronomy', 'naked eye', "
            s += "'" + datestr(startdate) + "', '" + datestr(enddate) + "', "
            s += "'"
            for m in minseps:
                s += conjstr(m[2], m[3], m[0], m[1])
            s += "', "
            s += "'astronomy/starry_moon.jpg', "
            s += "240, 169, "
            s += "'<a href=\"http://commons.wikimedia.org/wiki/File:Sachin_Nigam_-_starry_moon_%28by-sa%29.jpg\">starry moon on Wikimedia Commons</a>' ),"
            print(s)

        else:
            print("Conjunction of", self.andjoin(self.bodies), end=' ')
            print("lasts from %s to %s." % (datestr(startdate), datestr(enddate)))
            for m in minseps:
                print(" ", conjstr(m[2], m[3], m[0], m[1]))

    def merge(self, conj):
        """Merge in another Conjunction -- it must be that the two
           sets of pairs have bodies in common.
        """
        for p in conj.pairs:
            self.pairs.append(p)
        for body in conj.bodies:
            if body not in self.bodies:
                self.bodies.append(body)

class ConjunctionList:
    """A collection of Conjunctions -- no bodies should be shared
       between any of the conjunctions we contain.
    """
    def __init__(self):
        self.clist = []

    def __repr__(self):
        s = "ConjunctionList:"
        for c in self.clist:
            s += "\n    " + str(c)
        return s

    def add(self, b1, b2, date, sep):
        for i, c in enumerate(self.clist):
            if b1 in c or b2 in c:
                c.add(b1, b2, date, sep)
                # But what if one of the bodies is already in one of our
                # other Conjunctions? In that case, we have to merge.
                for cc in self.clist[i+1:]:
                    if b1 in cc or b2 in cc:
                        c.merge(cc)
                        self.clist.remove(cc)
                return

        # It's new, so just add it
        c = Conjunction()
        c.add(b1, b2, date, sep)
        self.clist.append(c)

    def closeout(self, observer):
        """When we have a day with no conjunctions, check the list
           and close out any pending conjunctions.
        """
        for c in self.clist:
            c.closeout(observer)
        self.clist = []

oneday = ephem.hour * 24

web_image = {
    # "Moon" : ("http://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Phase-088.jpg/240px-Phase-088.jpg", '''"<a href='http://commons.wikimedia.org/wiki/User:JayTanner/gallery'>Jay Tanner</a>"''', 240, 240),
    "Moon" : ("astronomy/Phase-088.jpg", '''"<a href='http://commons.wikimedia.org/wiki/User:JayTanner/gallery'>Jay Tanner</a>"''', 240, 240),
    "Mercury" : ("astronomy/mercury.jpg", "", 240, 182),
    "Venus" : ("astronomy/venus.jpg", "", 240, 192),
    # "Mars" : ("http://imgsrc.hubblesite.org/hu/db/images/hs-2001-24-a-small_web.jpg", "Hubble Space Telescope", 200, 200),
    "Mars" : ("astronomy/mars.jpg", "Hubble Space Telescope", 200, 200),
    # "Jupiter" : ("http://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Jupiter.jpg/240px-Jupiter.jpg", 'USGS, JPL and NASA', 240, 240),
    "Jupiter" : ("astronomy/Jupiter.jpg", 'USGS, JPL and NASA', 240, 240),
    # "Saturn" : ("http://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Saturn_%28planet%29_large.jpg/384px-Saturn_%28planet%29_large.jpg", "Voyager 2", 192, 240)
    "Saturn" : ("astronomy/saturn.jpg", "Voyager 2", 182, 240)
}

descriptions = {
    "Mars": " as a bright, reddish \"star\".",
    "Saturn": ". A small telescope will show its rings.",
    "Jupiter": ". With binoculars you can see its four brightest moons."
    }

def quotecsv(s):
    if ',' in s or '"' in s:
        return '"' + s.replace('"', '""') + '"'
    return s

def escape_singlequotes(s):
    return s.replace("'", "\\'")

def finish_planet(p, d, observer, output_format):
    if not planets_up[p]:
        return

    # Morning or evening? For that, we need to get a handle on
    # the ephem body object again.
    body = planets[planets_by_name.index(p)]
    observer.date = d
    transit = observer.previous_transit(body) - ephem.hour * timezone
    transit = list(ephem.Date(transit).tuple())
    if transit[3] < 3 or transit[3] > 12:
        when = "evening"
    else:
        when = "morning"

    if p == "Venus" or p == "Mercury":
        if when == "evening":
            isvis = p + " is visible in the early evening sky."
        else:
            isvis = p + " is visible in the morning sky."

    elif p in list(descriptions.keys()):
        desc = p + " is visible in the " + when + descriptions[p]
        if output_format == "csv":
            isvis = quotecsv(desc)
        elif output_format == "sql":
            isvis = escape_singlequotes(desc)
        else:
            isvis = desc

    elif p == "Moon":
        isvis = "The moon is visible in the " + when + "."

    else:
        isvis = p + " is visible in the " + when + "."

    # How about crescent info?
    if p in list(crescents.keys()):
        if crescents[p][0]:
            isvis += " A telescope will show a crescent from " \
                     + friendlydate(crescents[p][0])
            if crescents[p][1]:
                isvis += " to " + friendlydate(crescents[p][1])
            isvis += '.'
        crescents[p] = [ None, None ]

    if output_format == "csv" or output_format == "sql":
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

            if output_format == "csv":
                print("%s,%s,%s,,%s,,%s,%s,%s,%s" % \
                      (p, datestr(planets_up[p]), datestr(d), isvis,
                       img, w, h, cred))
            else:
                print("('%s', 'astronomy', 'naked eye', '%s', '%s', '%s', '%s', %s, %s, '%s' )," % \
                      (p, datestr(planets_up[p]), datestr(d), isvis,
                       img, w, h, cred))
    else:
        print(datestr(planets_up[p]), "to", datestr(d), ":", isvis)

    planets_up[p] = None


def run(start, end, observer, toolate, output_format):
    """Find planetary visibility between dates start and end,
       for an observer whose location has been set,
       between sunset and "toolate" on each date, where toolate is a GMT hour,
       e.g. toolate=7 means we'll stop at 0700 GMT or midnight MDT.
       toolate==None means look for anything between sunset and sunries.
    """
    global visible_planets, saw_conjunction

    d = start
    conjunctions = ConjunctionList()

    if output_format == "csv":
        print('name,start,end,time,longname,URL,'
              'image,image width,image height,image credit')
    elif output_format == "sql":
        print("INSERT INTO peecnatu_guides_dev.astronomy(common_name, "
              "guide_group, visibility, start, end, comments, image, "
              "image_width, image_height, image_credit) VALUES")
    else:
        print("Looking for planetary events between %s and %s:\n" % \
            (datestr(d), datestr(end)))

    def check_if_planet_up(planet, d):
        """If the planet is up on the given date, do housekeeping to remember
           that status, then return True if it's up, False otherwise.
           The date passed in is just a date; we will try different times
           on that date, including the immediately preceding sunset
           and a "toolate" hour of the night.
        """
        global crescents, planets_up, visible_planets, saw_conjunction

        # The moon is easy to see, so allow it half the alt of anything else.
        if planet.name == "Moon":
            if planet.alt < min_alt/2:   # moon isn't up
                return False
        elif planet.alt < min_alt:       # planet is not up
            return False

        # Planet is up.
        if not planets_up[planet.name]:
            planets_up[planet.name] = d;
        visible_planets.append(planet)

        if planet.name not in list(crescents.keys()):
            return True

        # Is it a crescent? Update its crescent dates.
        if planet.phase <= crescent_percent:   # It's a crescent now
            if not crescents[planet.name][0]:
                crescents[planet.name][0] = d
            else:
                crescents[planet.name][1] = d

        return True

    # Loop over the days in the time range:
    while d < end:

        # Set d to mid-day sometime, definitely before sunset
        midday = list(d.tuple())
        midday[3:6] = [12 - timezone, 0, 0]
        if midday[3] < 0:
            midday[3] += 12
        observer.date = ephem.date(tuple(midday))
        sunset = observer.next_setting(sun)

        # Stop at a fixed hour of the evening?
        if toolate:
            latenight = list(observer.date.tuple())
            latenight[3:6] = [toolate + 24 - timezone, 0, 0]
            latenight = ephem.date(tuple(latenight))
            if latenight < sunset:
                latenight += oneday

        # Stop at sunrise
        else:
            observer.date = sunset
            latenight = observer.next_rising(sun)

        if verbose:
            print("\n***", d, "from", sunset, "to", latenight)

        # We have two lists of planets: planets_up and visible_planets.
        # planets_up is a dictionary of the time we first saw each planet
        # in its current apparition. It's global, and used by finish_planet.
        # visible_planets is a list of planets currently visible.
        visible_planets = []
        for planet in planets:
            # A planet is observable this evening (not morning)
            # if its altitude at sunset OR its altitude at late-night
            # is greater than a visible_threshold
            observer.date = sunset
            planet.compute(observer)
            if verbose:
                print(observer.date, planet, "alt", planet.alt)
            if not check_if_planet_up(planet, observer.date):
                # If it's not up at sunset, try latenight
                observer.date = latenight
                if observer.date < sunset:
                    observer.date += oneday
                planet.compute(observer)
                if verbose:
                    print("  ", observer.date, planet, "alt", planet.alt)
                if not check_if_planet_up(planet, observer.date):
                    # Planet is not up. Was it up yesterday?
                    if planets_up[planet.name] and planet.name != "Moon":
                        finish_planet(planet.name, observer.date,
                                      observer, output_format)

        # print()
        # print(datestr(d), "visible planets:",
        #       ' '.join([p.name for p in visible_planets]))
        # print("planets_up:", planets_up)

        # Done with computing visible_planets.
        # Now look for conjunctions, anything closer than 5 degrees.
        # Split the difference, use a time halfway between sunset and latenight.
        saw_conjunction = False
        observer.date = ephem.date((sunset + latenight)/2)
        moon = planets[0]
        if len(visible_planets) > 1:
            for p, planet in enumerate(visible_planets):
                for planet2 in visible_planets[p+1:]:
                    sep = ephem.separation(planet, planet2)
                    # print(observer.date, "moon -", planet2.name, sep)
                    if sep <= max_sep:
                        # print (datestr(observer.date), planet.name,
                        #        planet2.name, sepstr(sep))
                        if verbose:
                            print("adding sep", planet.name, planet2.name,
                                  observer.date, sep)
                        conjunctions.add(planet.name, planet2.name,
                                         observer.date, sep)
                        saw_conjunction = True
                    elif planet == moon and sep <= moon_sep:
                        if verbose:
                            print("adding moon sep", planet.name, planet2.name,
                                  observer.date, sep)
                        conjunctions.add(planet.name, planet2.name,
                                         observer.date, sep)
                        saw_conjunction = True

        if not saw_conjunction:
            conjunctions.closeout(observer)

        # Add a day:
        d = ephem.date(d + oneday)

    if saw_conjunction:
        conjunctions.closeout(observer)
    for p in visible_planets:
        if p.name != "Moon":
            finish_planet(p.name, d, observer, output_format)


def moon_phases(start, end, output_format):
    d = ephem.previous_full_moon(start)
    d = ephem.previous_full_moon(d)
    print("Starting from", d)

    def output_moon_phase(d, phasename, img, attr):
        if output_format == "sql":
            print("('%s', 'astronomy', 'naked eye', '%s', '%s', '%s', "
                  "'%s', 240, 240, '%s')," % (phasename + " moon",
                                              datestr(d), datestr(d),
                                              phasename + " moon",
                                              img, attr))
        else:
            print(datestr(d), ":", phasename + " moon")

    while d <= end:
        d = ephem.next_first_quarter_moon(d)
        output_moon_phase(d, "First quarter", 'astronomy/Phase-088.jpg',
                          '<a href=\"http://commons.wikimedia.org/wiki/'
                          'File:Phase-088.jpg\">Jay Tanner</a>')
        d = ephem.next_full_moon(d)
        output_moon_phase(d, "Full", 'astronomy/Phase-180.jpg',
                          '<a href=\"http://commons.wikimedia.org/wiki/'
                          'File:Phase-180.jpg\">Jay Tanner</a>')
        d = ephem.next_last_quarter_moon(d)
        output_moon_phase(d, "Last quarter", 'astronomy/Phase-270.jpg',
                          '<a href=\"http://commons.wikimedia.org/wiki/'
                          'File:Phase-270.jpg\">Jay Tanner</a>')
        d = ephem.next_new_moon(d)
        output_moon_phase(d, "New", 'astronomy/New_Moon.jpg',
                          '<a href="https://commons.wikimedia.org/wiki/'
                          'File:New_Moon.jpg">QuimGil</a>')


if __name__ == '__main__':
    import sys, os

    if len(sys.argv) > 1 and (sys.argv[1] == "-h" or sys.argv[1] == "--help"):
        print("Usage: %s [-c|-s] start_date end_date"
              % os.path.basename(sys.argv[0]))
        print("  -c: CSV output")
        print("  -s: SQL output")
        print("  Otherwise output will be text")
        print("Dates in format yyyy/mm/dd [hh:mm] (PyEphem's preference)")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "-v":
        verbose = True
        sys.argv = sys.argv[1:]

    if len(sys.argv) > 1 and sys.argv[1] == "-c":
        output_format = "csv"
        sys.argv = sys.argv[1:]
    elif len(sys.argv) > 1 and sys.argv[1] == "-s":
        output_format = "sql"
        sys.argv = sys.argv[1:]
    else:
        output_format = "text"

    if len(sys.argv) > 1:
        start = ephem.date(sys.argv[1])
    else:
        start = ephem.date('2014/8/15 04:00')
    if len(sys.argv) > 2:
        end = ephem.date(sys.argv[2])
    else:
        end = ephem.date('2017/1/1')

    # Loop from start date to end date,
    # using a time of 10pm MST, which is 4am GMT the following day.
    # end = ephem.date('2016/1/1')
    # For testing, this spans a Mars/Moon/Venus conjunction:
    # d = ephem.date('2015/2/10 04:00')
    # end = ephem.date('2015/3/10')

    observer = ephem.Observer()
    observer.name = "Los Alamos"
    observer.lon = '-106.2978'
    observer.lat = '35.8911'
    observer.elevation = 2286  # meters, though the docs don't actually say

    # How late is too late to observe? E.g. 1 for 1 am, 23 for 11 pm.
    # None means we're interested in all events from sunset to sunrise.
    toolate = None

    try:
        run(start, end, observer, toolate, output_format)
        moon_phases(start, end, output_format)

    except KeyboardInterrupt:
        print("Interrupted")

