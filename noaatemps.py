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
# Description of the format:
# ftp://ftp.ncdc.noaa.gov/pub/data/gsod/GSOD_DESC.txt
#
# See also Eldan Goldenberg's raw_noaa_historical_weather_data_csv_converter
# http://eldan.co.uk/

import datetime
import urllib
import os
import gzip
import time
import sys
import matplotlib.pyplot as plt

verbose = True

# Table of NOAA fields and their positions within the file.
NOAA_fields = {
    'STN':   [0, 6],         # Station number (WMO/DATSAV3 number)
    'WBAN':  [7, 12],        # WBAN number
    'YEAR':  [14, 18],       # year
    'MODA':  [18, 22],       # month and day
    'TEMP':  [24, 30],       # mean temperature in degrees F. Missing: 9999.9
    'DEWP':  [35, 41],       # Mean dew point
    'SLP':   [46, 52],       # Mean sea level pressure, millibars
    'STP':   [57, 63],       # Mean station pressure
    'VISIB': [68, 73],       # Mean visibility in miles. Missing = 999.9
    'WDSP':  [78, 83],       # Mean wind speed in knots. Missing = 999.9
    'MXSPD': [88, 93],       # Max sustained wind speed in knots.
    'GUST':  [85, 100],      # Max wind gust in knots.
    'MAX':   [102, 108],     # Max temp in F
    'MIN':   [110, 116],     # Min temp in F
    'PRCP':  [118, 123],     # Total precipitation in inches
    'SNDP':  [125, 130],     # Snow depth in inches
    'FRSHTT': [132, 138],    # Codes, 1=yes, 0=no:
                             # Fog ('F' - 1st digit).
                             # Rain or Drizzle ('R' - 2nd digit).
                             # Snow or Ice Pellets ('S' - 3rd digit).
                             # Hail ('H' - 4th digit).
                             # Thunder ('T' - 5th digit).
                             # Tornado or Funnel Cloud ('T' - 6th digit).
}

class WeatherMean :
    '''Weather means for one location, over an extended period,
       encompassing means for several different fields keyed by
       name (e.g. MAX for high temp, MIN for low temp), averaged
       by month.
    '''
    def __init__(self, fields) :
        self.tots = {}
        self.num_obs = {}
        self.normalized = False
        for field in fields :
            self.tots[field] = [0.0] * 12
            self.num_obs[field] = [0] * 12

    def add_NOAA_obs(self, line) :
        '''Add observations for every field we're tracking
           by parsing a line from an NOAA data file.
           Increment nobs if the field isn't undefined.
        '''
        # Throw out the first line, with the keys.
        # XXX eventually might want to check that all the keys match
        # their value in this line.
        if line.startswith('STN---') :
            return

        # What fields are we looking for?
        fields = self.tots.keys()

        # Get the month: we need that first.
        month = int(line[NOAA_fields['MODA'][0]:NOAA_fields['MODA'][0]+2]) - 1

        # Break into fields according to the NOAA spec.
        for field in NOAA_fields.keys() :
            if field in fields :
                val = float(line[NOAA_fields[field][0]:NOAA_fields[field][1]])
                # NOAA uses 999.9 or 9999.9 to denote missing data.
                # So anything over 999 is likely missing; don't count it.
                if val < 999 :
                    self.tots[field][month] += val
                    self.num_obs[field][month] += 1

    def normalize(self) :
        for field in self.tots.keys() :
            for month in range(12) :
                if self.num_obs[field][month] > 0 :
                    self.tots[field][month] /= self.num_obs[field][month]
        self.normalized = True

    def get_data(self, field) :
        '''Return the 12-month means for the indicated field name.'''
        if not self.normalized :
            self.normalize()
        return self.tots[field]

def findstations(stationnames) :
    '''Search through ish-history.txt for given station names.
       stationnames is a list of strings like 'KSJC'
       and we return a dictionary of lists of the first two numbers from the
       first match in the file for each station, plus the long station name.
       E.g. pass in ['KSJC', 'KFLG']
       it should find these two lines:
724945 23293 NORMAN Y MINETA SAN           US US CA KSJC  +37359 -121924 +00152    19730101 20121212
723750 03103 FLAGSTAFF AIRPORT             US US AZ KFLG  +35144 -111666 +21391    20050101 20121212
       and return { 'KSJC' : [724945, 23293, 'NORMAN Y MINETA SAN'],
                    'KFLG' : [723750, 03103, 'FLAGSTAFF AIRPORT'] }
    '''
    result = {}
    ish = open('ish-history.txt')
    for line in ish :
        for station in stationnames :
            if station not in result.keys() :
                if station == line[52:56] :
                    result[station] = [ line[0:6], line[7:12],
                                        line[13:43].strip() ]
    ish.close()
    return result

def noaa_files(stationnames, years) :
    '''Call findstations() to get the station codes, then build a list
       of URLs we'll need to download and parse.
       Returns a dictionary like
    {'KFLG':
      ['ftp://ftp.ncdc.noaa.gov/pub/data/gsod/2011/723750-03103-2011.op.gz',
       'ftp://ftp.ncdc.noaa.gov/pub/data/gsod/2012/723750-03103-2012.op.gz'],
     'KSJC':
      ['ftp://ftp.ncdc.noaa.gov/pub/data/gsod/2011/724945-23293-2011.op.gz',
       'ftp://ftp.ncdc.noaa.gov/pub/data/gsod/2012/724945-23293-2012.op.gz']}
    '''
    stationcodes = findstations(stationnames)
    urldict = {}
    for station in stationnames :
        urldict[station] = []
        for y in years :
            url = 'ftp://ftp.ncdc.noaa.gov/pub/data/gsod/%d/%s-%s-%d.op.gz' % \
                   (y, stationcodes[station][0], stationcodes[station][1], y)
            urldict[station].append(url)
    return urldict

if __name__ == '__main__' :
    if len(sys.argv) <= 1 :
        stations = [ 'KSJC', 'KFLG' ]
    else :
        stations = sys.argv[1:]
    years = range(1991, 2012)
    #years = [ 2012 ]
    urls = noaa_files(stations, years)
    fields = ['TEMP', 'MAX', 'MIN', 'PRCP', 'SNDP']
    download_dir = "."
    monthnames = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    colors  = 'brgcmky'
    markers = 'o+sv*p<>^hH.'

    means = {}
    for station in stations :
        means[station] = WeatherMean(fields)

    # Get all the stationcodes. Best to do this all at once since it
    # requires parsing a large file.
    stationcodes = findstations(stations)

    print '     ',
    for mn in monthnames :
        print '  ' + mn,
    print

    for i, station in enumerate(stations) :
        for y in years :
            basename = '%s-%s-%d.op.gz' % (stationcodes[station][0],
                                           stationcodes[station][1], y)
            url = 'ftp://ftp.ncdc.noaa.gov/pub/data/gsod/%d/%s' % (y, basename)
            filename = os.path.join(download_dir, basename)

            # Download the file if it's not already here:
            if not os.path.exists(filename):
                try:
                    if verbose: print "downloading", url
                    urllib.urlretrieve(url, filename)
                except IOError as e:
                    print(e)
                    print "Skipping", filename, "for station", station
                    # NOAA has a lot of missing files -- many stations
                    # don't have anything before 1995.
                    # Since it will probably get this error every time,
                    # create a zero-length file there:
                    emptyfile = open(filename, 'w')
                    emptyfile.close()
                    continue

            # Now the file should be there.
            fp = gzip.open(filename)
            for line in fp :
                means[station].add_NOAA_obs(line)
            fp.close()

        print "===============", station, y, stationcodes[station][2]

        for field in ('TEMP', 'MAX', 'MIN', 'PRCP', 'SNDP') :
            data = means[station].get_data(field)
            print '%6s' % field,
            for m in range(12) :
                print '%5.2f' % data[m],
            print

        color = colors[i%len(colors)] + markers[i%len(markers)] + '-'
        plt.plot(means[station].get_data('MAX'), color,
                 label=stationcodes[station][2])
        plt.plot(means[station].get_data('MIN'), color, markerfacecolor='none')

    plt.legend()
    plt.show()


