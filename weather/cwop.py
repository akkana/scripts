#!/usr/bin/env python

# Parse data from Citizen Weather Observation Program stations.
# http://www.wxqa.com/states/AZ.html list, citizen weather obs program stations

# To get data, find the "CWOP QC" from the table, then, e.g. for the QC=AS857,
# get a CSV for the last 7 days at
# http://weather.gladstonefamily.net/cgi-bin/wxobservations.pl?site=AS857&days=7

import sys
import urllib2
import math

def find_station_by_coordinates(lat, lon):
    request = urllib2.Request('http://wxqa.com/APRSWXNETStation.txt')
    response = urllib2.urlopen(request)

    # Format:
    #  ProviderId|AFOS(HB5)Id|StationName|Elevation|Latitude|Longitude|localTZ|
    #  LocationDesc|StationType|NumInst|NumLevels|Maint/CalibSch|SiteDesc|
    #
    #  ProviderId  - Data provider station id
    #  AFOS(HB5)Id - The AFOS or Handbook 5 id (NWS ID)
    #  Name        - Text name of station
    #  Elevation   - Elevation of station
    #  Latitude    - Latitude of station
    #  Longitude   - Longitude of station
    #  localTZ     - local Timezone (e.g. GMT)
    #  LocationDesc- Location/address of Station (Text)
    #  StationType - Type of station (i.e. tower, surface, floating platform)
    #  NumInst     - The number of reporting instruments for the station
    #  NumLevels   - Number of Reporting Levels for the data (Level information
    #                should be provided in the instrument table.)
    #  Maint/CalSch- Frequency of Maintenance/Calibration
    #  SiteDesc    - A text description of the site surroundings
    #
    #  *Note* '#' in column 1 to comment out the entry.
    id = None
    mindist = 999999.0
    for line in response:
        if line[0] == '#':
            continue
        fields = line.split('|')
        slat = float(fields[4])
        slon = float(fields[5])
        dist = math.sqrt((slat - lat)**2 + (slon - lon)**2)
        if dist < mindist:
            # Nearest station so far: save it.
            mindist = dist
            id = fields[1]
            name = fields[2]
            ele = fields[3]
            savelat = slat
            savelon = slon
            numinst = fields[9]

    response.close()
    if not id:
        print "Couldn't find a station, sorry!"
        return None
    return id, name, int(ele), savelat, savelon, numinst

def get_data(stationid):
    request = urllib2.Request('http://weather.gladstonefamily.net/cgi-bin/wxobservations.pl?site=%s&days=7' % stationid)
    response = urllib2.urlopen(request)
    # Format: comma separated.
    # "Time (UTC)","Barometric Pressure (mbar)","Temperature (degrees F)",
    # "Dewpoint (degrees F)","Relative Humidity (%)","Wind speed (mph)",
    # "Wind direction (degrees)","Analysis Barometric Pressure (mbar)",
    # "Analysis Temperature (degrees F)","Analysis Dewpoint (degrees F)",
    # "Analysis Relative Humidity (%)","Analysis Wind speed (mph)",
    # "Analysis Wind direction (degrees)"

    # To get the current temp, we generally want the last complete line.
    # Which may not be the actual last line of the file -- the last line
    # may be partial.
    save_fields = None
    save_nonblank = 0
    for line in response:
        fields = line.split(',')

        # How many of the fields are non-blank?
        # Don't save a line if it has more blank fields than the previous best.
        nonblank = sum(1 for f in fields if f)
        if nonblank >= save_nonblank:
            save_nonblank = nonblank
            save_fields = fields

    response.close()

    if not save_fields:
        print "No data!"
        return

    return fields

if __name__ == '__main__':
    id, name, ele, savelat, savelon, numinst = \
        find_station_by_coordinates(float(sys.argv[1]), float(sys.argv[2]))
    print "ID", id, name, "ele", int(ele), "coords", savelat, savelon, \
        numinst, "instrument reporting"

    fields = get_data(id)
    print "Time", fields[0], "Temp", fields[2]
    print "Dew point", fields[3], "Wind speed", fields[5]


