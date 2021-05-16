#!/usr/bin/env python3

# How did Kepler measure planets' oppositions without an accurate clock?
# One theory: a planet's opposition is right in the middle of its
# retrograde loop. Compare those two positions.

# For testing: the 2018 opposition is at July 27 0507 UTC.
# Closest approach is July 31 0751.

# To pick a random date, XEphem says on 2018-07-25 00:00 UTC,
# Mars is at RA 20h34m3.53s dec -25^21'16.6"
# or 20.567647222222224, -25.35461111111111  0.38776205 AU
# pyastro says <Longitude 308.50560408 deg>, <Latitude -25.35362011 deg>)
# or 20.567040271697675, -25.353620111328397
# pyephem says '20:35:08.94', '-25:17:08.8'  0.3877919614315033 AU
# or 20.585817513053833, -25.285783243254137
# JPL Horizons says:
# R.A._(ICRF/J2000.0)_DEC  APmag  S-brt            delta      deldot    S-O-T /r    S-T-O
# 20 34 02.32 -25 21 07.4  -2.76   3.89 0.38779322689580  -1.5503477 173.0418 /L   5.0383
# or 20.56731111111111, -25.352055555555555

from astropy.time import Time, TimeDelta
from astropy.coordinates import solar_system_ephemeris, EarthLocation
from astropy.coordinates import get_body, Angle
from astropy.coordinates.distances import Distance
from astropy import units

import sys
import os
import math
import argparse

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

# Planet we're studying:
planetname = "mars"

# How many days on either side of opposition to monitor
# (mostly useful when plotting points graphically):
EXTRA_DAYS = 50

class OppRetro(object):

    def __init__(self, location):
        self.location = location

        self.save_all_points = False

        # planettrack will be a list of tuples:
        # (date, RA, dec, dist (AU), flags)
        # Depending on save_all_points it may have all the points,
        # or only points where something happens.
        self.planettrack = None

    def find_opp_and_retro(self, start_time):
        cur_time = Time(start_time)

        last_RA = 0.
        last_dist = Distance(999, unit=units.au)
        pre_closest = True
        self.retrograding = False
        retro_start = None
        retro_end = None
        opptime = None

        # Earth location to use for calculating Mars' position.
        # Setting it to None will (I think? docs aren't clear) calculate
        # from the center of the Earth; this is much faster, skips
        # calculations like parallax due to earth's rotation,
        # and avoids seeing a lot of spurious retrograde/direct
        # transitions due solely to the observer's position changing
        # as the earth rotates.
        location = None

        # A place to store the data points
        self.planettrack = []

        # When a planet is approaching opposition, its elongation is negative.
        # When it flips to positive (-180 to 180), it just passed opposition.
        # Can't check for exactly 180 if we're only checking time coarsely.
        last_elong = -1

        # We'll look for the end of retrograde then go a few days
        # past it; but first, put a limit on how far we can go.
        end_time = cur_time + TimeDelta(300, format='jd')

        # Initially, go one day at a time:
        coarsemode = TimeDelta(1, format='jd')
        # but in fine mode, we'll go one hour at a time:
        finemode = TimeDelta(60*60, format='sec')
        # and near opposition we'll go even finer for a few days:
        superfinemode = TimeDelta(60 * 5, format='sec')

        timeslice = coarsemode

        while cur_time < end_time:
            cur_time += timeslice

            mars = get_body(planetname, cur_time)

            flags = ''

            # Are we starting or stopping retrograde?
            if ( (mars.ra == last_RA) or
                 (mars.ra < last_RA and not self.retrograding) or
                 (mars.ra > last_RA and self.retrograding) ):
                # Are we still in coarse mode? If so, jump back
                # in time a few days and go to fine mode.
                if timeslice == coarsemode:
                    print("Switching to fine mode on", cur_time)
                    print("         RA", mars.ra.hour, ", dec", mars.dec.degree)
                    timeslice = finemode
                    cur_time -= TimeDelta(EXTRA_DAYS, format='jd')
                    continue

                # We're in fine mode. Record dates when the planet
                # starts or ends retrograde, hits opposition or makes
                # its closest approach.

                if self.retrograding:
                    flags += END_RETROGRADE
                    # Don't consider this the actual end of retrograde
                    # unless we're already past opposition.
                    # There are potentially a lot of false retrogrades.
                    # We can get them from parallax if we calculate
                    # Mars' position from a specific earth location;
                    # but even if we don't, pyastro gives us a lot
                    # of false little retrogrades and I don't know why.
                    if opptime:
                        retro_end = cur_time
                else:
                    flags += START_RETROGRADE
                    retro_start = cur_time

                if mars.ra == last_RA:
                    flags += STATIONARY

                self.retrograding = not self.retrograding

            # Calculate elongation to find the opposition time:
            sun = get_body('sun', cur_time)
            elongation = (mars.ra - sun.ra).degree
            # print(cur_time, "\n  RA",
            #       mars.ra.hour, "dec", mars.dec.degree,
            #       "elongation", elongation)
            if last_elong > 180. and elongation <= 180.:
                if timeslice == superfinemode:
                    flags += OPPOSITION
                    opptime = cur_time
                    timeslice = finemode
                    print("Opposition on", cur_time, ", switching back to fine")
                    # XXX it would be nice not to go back to finemode
                    # until after we've found closest approach.
                    # But astropy randomly finds a closest approach
                    # date weeks before the actual closest approach,
                    # at the start of retrograde.
                else:
                    # Looks like opposition. But let's go back a day and
                    # get a finer view of the time.
                    print("Switching to superfine mode on", cur_time)
                    timeslice = superfinemode
                    cur_time -= TimeDelta(1, format='jd')

            if mars.distance >= last_dist and pre_closest:
                flags += CLOSEST_APPROACH
                # self.find_parallax(cur_time)
                pre_closest = False

            elif mars.distance < last_dist:  # receding
                pre_closest = True

            if flags or self.save_all_points:
                self.planettrack.append([cur_time.datetime,
                                         mars.ra.radian, mars.dec.radian,
                                         mars.distance.km, flags])

            last_RA = mars.ra
            last_dist = mars.distance
            last_elong = elongation

            # If we've seen the opposition as well as retro_start and retro_end
            # then we're done. Switch back to coarse mode and record a
            # few more days.
            if timeslice == finemode and retro_start and retro_end and opptime:
                timeslice = coarsemode
                end_time = cur_time + TimeDelta(EXTRA_DAYS, format='jd')

        # We're done calculating all the points.
        # Now calculate the retrograde midpoint, if we have both start and end.
        if retro_start and retro_end:
            mid_retro_date = retro_start + (retro_end - retro_start) / 2
            mars = get_body(planetname, mid_retro_date)

            # Insert that into our planettrack list:
            for i, point in enumerate(self.planettrack):
                if point[IDATE] == mid_retro_date:
                    point[IFLAGS] += MIDPOINT_RETRO
                    break
                elif point[IDATE] > mid_retro_date:
                    self.planettrack.insert(i, [mid_retro_date.datetime,
                                                mars.ra.radian, mars.dec.radian,
                                                mars.distance.km,
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
                      (self.flags_to_string(point[IFLAGS]), str(point[IDATE]),
                       self.rads_to_hours(point[IRA]),
                       self.rads_to_degrees(point[IDEC]),
                       point[IDIST] / 1.609344))

    def find_parallax(self, date):
        '''Find the maximum parallax of self.planet on the given date
           from self.observer's location -- in other words, the difference
           in Mars' position between the observer's position and an
           observer at the same latitude but opposite longitude:
           this tells you you how much difference you would see from
           your position if Mars didn't move between your sunrise and sunset.
        '''
        # To calculate from a point on the equator, set lat to 0.
        observer_loc = EarthLocation.from_geodetic(self.location.lon,
                                                   self.location.lat,
                                                   self.location.height)

        # Specify the anti-point.
        # This isn't really an antipode unless lat == 0.
        antipode_loc = EarthLocation.from_geodetic(-observer.lon,
                                                   observer.lat,
                                                   observer.height)

        # XXX Oops, astropy doesn't offer next_rising etc.
        # so we'll need a function to find that before this
        # function can be implemented since it only works
        # when the planet is on the horizon so both the observer
        # and the anti-observer can see it.
        risetime = find_next_rising(planetname, date)

        obs_planet = get_body(planetname, risetime, observer_loc)
        ant_planet = get_body(planetname, risetime, antipode_loc)

        # First, calculate it the straightforward way using the arctan:
        print()
        mars_dist_miles = mars.distance.km / 1.609344
        print("Miles to Mars:", mars_dist_miles)
        earth_mean_radius = 3958.8    # in miles
        half_dist = earth_mean_radius * math.cos(observer_loc.lat)
        print("Distance between observers:", 2. * half_dist)
        par = 2. * math.atan(half_dist / mars_dist_miles) \
              * 180. / math.pi * 3600.
        print("Calculated parallax (arcsec):", par)

        # See what astropy calculates as the difference between observations:
        print()
        print("parallax on %s: RA %f, dec %f" % (antipode.date,
                                                 obs_planet.ra - ant_planet.ra,
                                             obs_planet.dec - ant_planet.dec))
        total_par = (math.sqrt((obs_planet.ra.radians
                                - ant_planet.ra.radians)**2
                               + (obs_planet.dec.radians
                                - ant_planet.dec.radians)**2)
                     * 180. * 3600. / math.pi)
        print("Total parallax (sum of squares): %f arcseconds" % total_par)
        print()

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

        return ', '.join(l)

if __name__ == '__main__':
    # PEEC Los Alamos:
    # Google Maps lookups sometimes fail,
    # especially if you run over and over while testing.
    # loc = EarthLocation.of_address('2600 Canyon Road, Los Alamos, New Mexico 87544')
    # So instead, specify coordinates directly:
    loc = EarthLocation.from_geodetic('-106:18.36', '35:53.09', 2100.)

    # I'm not clear what this does, or what is used if you don't
    # specify builtin:
    solar_system_ephemeris.set('builtin')

    parser = argparse.ArgumentParser()
    parser.add_argument('-w', "--window", dest="window", default=False,
                        action="store_true", help="Show a graphical window")
    args = parser.parse_args(sys.argv[1:])

    start_date = Time('2018-06-25 00:00')

    oppy = OppRetro(loc)
    try:
        oppy.find_opp_and_retro(start_date)
    except KeyboardInterrupt:
        print("Interrupt")

