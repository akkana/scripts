#! /usr/bin/env python

# Print a table of mean temperatures (and other weather data) per month
# for several locations.
#
# Copyright 2013 by Akkana Peck.
#
# This program is free software; you can redistribute it and/or
#        modify it under the terms of the GNU General Public License
#        as published by the Free Software Foundation; either version 2
#        of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
#        but WITHOUT ANY WARRANTY; without even the implied warranty of
#        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#        GNU General Public License for more details.
# The licence text is available online at:
#        http://www.gnu.org/licenses/gpl-2.0.html
#
# Data comes from
# ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/
# with a format described in
# ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README
# Download these two files for max and min temp averages:
# ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/ghcnm.tmax.latest.qca.tar.gz
# ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/ghcnm.tmin.latest.qca.tar.gz

from meantemps import *
import sys, os
import urllib
import tarfile

verbose = True

class GHCNMWeatherMean(WeatherMean) :
    '''Weather means for one station, over an extended period,
       encompassing means for several different fields keyed by
       name (e.g. MAX for high temp, MIN for low temp), averaged
       by month. Parsed from NOAA GHCNM data.
    '''
    # Some static variables, common to all stations:
    files_downloaded = False
    download_dir = "."
    baseurl = 'ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/'
    maxbasename = 'ghcnm.tmax.latest.qca.tar.gz'
    minbasename = 'ghcnm.tmin.latest.qca.tar.gz'
    maxtarfilename = os.path.join(download_dir, maxbasename)
    mintarfilename = os.path.join(download_dir, minbasename)

    def __init__(self, fields) :
        WeatherMean.__init__(self, fields)

        self.minyears = {}
        self.maxyears = {}
        for field in fields :
            self.minyears[field] = 3000
            self.maxyears[field] = 0

    @staticmethod
    def download_files() :
        '''Make sure we've downloaded the necessary files.
           This should only have to be done once.
        '''
        if GHCNMWeatherMean.files_downloaded :
            return

        if not os.path.exists(GHCNMWeatherMean.maxtarfilename) :
            print "Downloading", GHCNMWeatherMean.maxbasename
            urllib.urlretrieve(GHCNMWeatherMean.baseurl + \
                                   GHCNMWeatherMean.maxbasename,
                               GHCNMWeatherMean.maxtarfilename)

            #tar.extractall(path="foo")
            # Now we should have a directory called
            # ghcnm.v3.2.1.20130413
            # Why that? Will it change? I have no idea. So I guess
            # we'd better search for any ghcnm.v3* directory. Gah!

        if not os.path.exists(GHCNMWeatherMean.mintarfilename) :
            print "Downloading", GHCNMWeatherMean.minbasename
            urllib.urlretrieve(GHCNMWeatherMean.baseurl + \
                                   GHCNMWeatherMean.minbasename,
                               GHCNMWeatherMean.mintarfilename)

        # Now we think they're both there.
        GHCNMWeatherMean.files_downloaded = True

    def add_obs(self, line, field) :
        '''Add observations for a year and station
           by parsing a line from a GHCNM data file.
           Increment nobs if the field isn't undefined.
        '''
        # Typical line:
        # 101603550001997TMAX-9999   -9999    1730  G 1950  G 2310  G 2670  G 2670  G-9999   -9999   -9999    2100  G 1850  G
        # We've already established that the first 11 digits match
        # our station by the time add_obs is called.

        year = int(line[11:15])
        if year < self.minyears[field] : self.minyears[field] = year
        if year > self.maxyears[field] : self.maxyears[field] = year

        # Print another line with the raw strings,
        # to see if we're converting them properly
        if verbose :
            print year,
            for month, start in enumerate(range(20, 109, 8)) :
                num = line[start:start+4]
                print '%5s' % num,
            print
            print '%11s' % '',

        # Data vals start every 8 chars and occupy 5 chars
        if verbose :
            print year,
        for month, start in enumerate(range(20, 109, 8)) :
            num = line[start:start+4]
            if num == '9999' :
                if verbose :
                    print '     ',
                continue
            self.tots[field][month] += (int(num) / 100.0)
            # Convert C to F
            # self.tots[field][month] += (int(num) / 100.0) * (2.12-.32) + 32
            self.num_obs[field][month] += 1
            if verbose :
                print "%5.2f" % (int(num) / 100.0),
        if verbose :
            print

    @staticmethod
    def compile_temps(stations, means, field) :
        '''Parse a GHCNM file, either of mean max temperatures or mean mins.
           A file contains entries for many different stations;
           each line is a different station and year.
           Return a dictionary with year: [12 temps]
        '''

        # Use the appropriate filename based on the field:
        GHCNMWeatherMean.download_files()
        if field == 'MAX' :
            filename = GHCNMWeatherMean.maxtarfilename
        elif field == 'MIN' :
            filename = GHCNMWeatherMean.mintarfilename
        else :
            print "Unknown field", field
            return

        tar = tarfile.open(filename)
        # The tar file should have two members, with names like
        # ./ghcnm.v3.2.1.20130413/ghcnm.tmax.v3.2.1.20130413.qca.dat
        # ./ghcnm.v3.2.1.20130413/ghcnm.tmax.v3.2.1.20130413.qca.inv
        # The .dat is the data, the .inv is the stations,
        # though their documentation doesn't say that anywhere.
        for fnam in tar.getnames() :
            if os.path.splitext(fnam)[1] == '.dat' :
                fp = tar.extractfile(fnam)

                for line in fp :
                    # Is the station one of the ones we're looking for?
                    if line[0:11] not in stations :
                        continue
                    print line[0:11],
                    means[line[0:11]].add_obs(line, field)

                fp.close()
                break
        tar.close()

if __name__ == '__main__' :

    # Moffet Field, Moab, Flagstaff
    stations = [ '42574509003', '42500425733', '42572376004' ]
    fields = [ 'MIN', 'MAX' ]
    means = {}
    for station in stations :
        means[station] = GHCNMWeatherMean(['MIN', 'MAX'])

    for field in fields :
        GHCNMWeatherMean.compile_temps(stations, means, field)

    display_results(means)

