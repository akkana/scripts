#!/usr/bin/env python3

# How did Kepler measure planets' oppositions without an accurate clock?
# One theory: a planet's opposition is right in the middle of its
# retrograde loop. Compare those two positions.

import ephem
from ephem import cities

import sys
import os
import math
import argparse

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gdk

import cairo
from gi.repository import Pango
from gi.repository import PangoCairo

# Codes for events
START_RETROGRADE = 's'
END_RETROGRADE = 'e'
OPPOSITION = 'o'
CLOSEST_APPROACH = 'c'
STATIONARY = 'S'
MIDPOINT_RETRO = 'm'

# Codes for indices into planettrack items:
IDATE = 0
IRA = 1
IDEC = 2
IDIST = 3
IFLAGS = 4

class OppRetro(object):

    def __init__(self, observer):
        if type(observer) is ephem.Observer:
            self.observer = observer
        elif observer == "Los Alamos":
            # Avoid problems from repeated city lookup
            self.observer = ephem.Observer()
            self.observer.name = "Los Alamos"
            self.observer.lon = '-106:18.36'
            self.observer.lat = '35:53.09'
            self.observer.elevation = 2100
        else:
            self.observer = self.lookup_observer(observer)

        print("observer is", self.observer)

        self.planet = ephem.Mars()

        self.save_all_points = False

        # planettrack will be a list of tuples:
        # (date, RA (radians), dec (radians), dist (AU), flags)
        # Depending on save_all_points it may have all the points,
        # or only points where something happens.
        self.planettrack = None

    def set_time(self, d):
        if type(d) is ephem.Date:
            self.observer.date = d
        else:
            self.observer.date = ephem.date(d)

    def find_opp_and_retro(self, start_date):
        self.observer.date = start_date

        # Find retrograde
        last_RA = 0.
        last_dist = 999  # earth_distance is in AU and will be less than this
        pre_closest = True
        self.retrograding = False
        retro_start = None
        retro_end = None

        # A place to store the data points
        self.planettrack = []

        # When a planet is approaching opposition, its elongation is negative.
        # When it flips to positive (-180 to 180), it just passed opposition.
        # Can't check for exactly 180 if we're only checking time coarsely.
        last_elong = -1
        end_date = ephem.Date(self.observer.date + 170)
        while self.observer.date < end_date:
            # Add time, in days or fractions thereof.
            self.observer.date = ephem.Date(self.observer.date + .01)
            # self.observer.date = ephem.Date(self.observer.date + 1)

            # It's important to use compute(date), not compute(observer).
            # The latter will include parallax, and will show shifts
            # from retrograde to direct motion on multiple days
            # because (apparently) the parallax is greater than the
            # motion of the planet on those days, at least for Mars.
            # self.planet.compute(self.observer)
            self.planet.compute(self.observer.date)

            flags = ''

            # Are we starting or stopping retrograde?
            if ( (self.planet.ra == last_RA) or
                 (self.planet.ra < last_RA and not self.retrograding) or
                 (self.planet.ra > last_RA and self.retrograding) ):
                if self.retrograding:
                    flags += END_RETROGRADE
                    retro_end = self.observer.date
                else:
                    flags += START_RETROGRADE
                    retro_start = self.observer.date

                if self.planet.ra == last_RA:
                    flags += STATIONARY

                self.retrograding = not self.retrograding

            # print(self.observer.date, "Elongation:", self.planet.elong)
            if last_elong < 0 and self.planet.elong > 0:
                flags += OPPOSITION

            if self.planet.earth_distance >= last_dist and pre_closest:
                flags += CLOSEST_APPROACH
                self.find_parallax(self.observer.date)
                pre_closest = False

            elif self.planet.earth_distance < last_dist:  # receding
                pre_closest = True

            if flags or self.save_all_points:
                self.planettrack.append([self.observer.date.datetime(),
                                         float(self.planet.ra),
                                         float(self.planet.dec),
                                         self.planet.earth_distance,
                                         flags])

            last_RA = self.planet.ra
            last_dist = self.planet.earth_distance
            last_elong = self.planet.elong

        # We're done calculating all the points.
        # Now calculate the retrograde midpoint, if we have both start and end.
        if retro_start and retro_end:
            mid_retro_date = ephem.Date((retro_start + retro_end) / 2)
            self.observer.date = mid_retro_date
            self.planet.compute(self.observer.date)

            # Insert that into our planettrack list:
            for i, point in enumerate(self.planettrack):
                if point[IDATE] == mid_retro_date:
                    point[IFLAGS] += MIDPOINT_RETRO
                    break
                elif point[IDATE] > mid_retro_date.datetime():
                    self.planettrack.insert(i, [mid_retro_date.datetime(),
                                                float(self.planet.ra),
                                                float(self.planet.dec),
                                                self.planet.earth_distance,
                                                MIDPOINT_RETRO])
                    # We've just changed a list in the middle of looping
                    # over that list, but it's okay because we're breaking out.
                    break
        else:
            print("don't have both retro start and end")

        # Now print what we found.
        print("%20s %-19s  %-11s   %-10s %s" % ('', 'Date',
                                               'RA', 'Dec', 'Dist (mi)'))
        for point in self.planettrack:
            if point[IFLAGS]:
                # print("%20s %-19s  %-11s  %-10s %d" % \
                #       (self.flags_to_string(point[4]), str(point[0]),
                #        point[1], point[2],
                #        point[3] * 9.2956e7))
                print("%20s %-19s  %-11.7f  %-10.7f %d" % \
                      (self.flags_to_string(point[IFLAGS]),
                       point[IDATE].strftime("%Y-%m-%d %H:%M"),
                       self.rads_to_hours(point[IRA]),
                       self.rads_to_degrees(point[IDEC]),
                       point[IDIST] * 9.2956e7))
                if OPPOSITION in point[IFLAGS]:
                    opp_RA = point[IRA]
                    opp_dec = point[IDEC]
                if MIDPOINT_RETRO in point[IFLAGS]:
                    mpr_RA = point[IRA]
                    mpr_dec = point[IDEC]

        if opp_RA and mpr_RA:
            degdiff = self.rads_to_degrees(math.sqrt((opp_RA - mpr_RA)**2
                                                     + (opp_dec - mpr_dec)**2))
            print("Difference between opposition and midpoint of retrograde:")
            if (degdiff > 2):
                print(degdiff, "degrees")
            elif (degdiff * 60. > 2):
                print(degdiff * 60., "arcmin")
            elif (degdiff > 5):
                print(degdiff * 3600., "arcsec")

    def find_parallax(self, date):
        '''Find the maximum parallax of self.planet on the given date
           from self.observer's location -- in other words, the difference
           in Mars' position between the observer's position and an
           observer at the same latitude but opposite longitude:
           this tells you you how much difference you would see from
           your position if Mars didn't move between your sunrise and sunset.
        '''
        save_date = self.observer.date

        # https://www.quora.com/Is-it-possible-to-measure-the-distance-to-Mars-using-a-telescope-and-the-parallax-method
        # says it should vary between 361.9 arc sec > a > 51.6 arc sec,
        # but I think he's smoking something.
        # So let's calculate it.
        observer = ephem.Observer()
        observer.name = "Observer"
        # To calculate from a point on the equator, set observer.lat to 0.
        observer.lat = self.observer.lat
        observer.lon = self.observer.lon
        observer.elevation = 0

        antipode = ephem.Observer()
        antipode.name = "Anti-point"
        antipode.lat = observer.lat
        antipode.lon = 360 - self.observer.lon
        antipode.elevation = 0

        observer.date = observer.next_rising(self.planet, start=date)
        self.planet.compute(observer)
        our_ra = self.planet.ra
        our_dec = self.planet.dec
        antipode.date = observer.date
        self.planet.compute(antipode)
        antipode_ra = self.planet.ra
        antipode_dec = self.planet.dec

        # Calculate it the straightforward way using trig:
        print()
        mars_dist_miles = self.planet.earth_distance * 9.2956e7
        print("Miles to Mars:", mars_dist_miles)
        earth_mean_radius = 3958.8    # in miles
        half_dist = earth_mean_radius * math.cos(observer.lat)
        print("Distance between observers:", 2. * half_dist)
        par = 2. * math.atan(half_dist / mars_dist_miles) * 180 / math.pi * 3600
        print("Calculated parallax (arcsec):", par)

        # See what pyephem calculates as the difference between observations:
        print()
        print("     Us:", our_ra, our_dec)
        print("Anti-pt:", antipode_ra, antipode_dec)
        print("parallax on %s: RA %f, dec %f" % (antipode.date,
                                                 our_ra - antipode_ra,
                                                 our_dec - antipode_dec))
        total_par = (math.sqrt((our_ra - antipode_ra)**2 +
                               (our_dec - antipode_dec)**2)
                     * 180. / math.pi * 3600.)
        print("Total parallax (sum of squares): %f arcseconds" % total_par)
        print()

        # Set planet back to its previous position,
        # since we're in the middle of ongoing computations:
        self.planet.compute(self.observer.date)

    @staticmethod
    def rads_to_degrees(a):
        return float(a) * 180. / math.pi

    @staticmethod
    def rads_to_hours(a):
        return float(a) * 12. / math.pi

    @staticmethod
    def flags_to_string(flags):
        l = []
        if OPPOSITION in flags:
            l.append("Opposition")
        if CLOSEST_APPROACH in flags:
            l.append("Closest approach")
        if STATIONARY in flags:
            l.append("Stationary")
        if START_RETROGRADE in flags:
            l.append("Start retrograde")
        if END_RETROGRADE in flags:
            l.append("End retrograde")
        if MIDPOINT_RETRO in flags:
            l.append("Retrograde midpoint")

        return ','.join(l)

    @staticmethod
    def lookup_observer(city):
        try:
            return ephem.city(city)
        except KeyError:
            try:
                return cities.lookup(city)
            except ValueError:
                raise RuntimeError("I don't know where %s is, sorry" % city)

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-w', "--window", dest="window", default=False,
    #                     action="store_true", help="Show a graphical window")
    # args = parser.parse_args(sys.argv[1:])

    start_date = ephem.Date('2018/6/25 0:00')

    cityname = "Los Alamos, NM"
    # cityname = "Prague"

    oppy = OppRetro(cityname)
    oppy.find_opp_and_retro(start_date)

