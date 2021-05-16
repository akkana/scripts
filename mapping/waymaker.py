#!/usr/bin/env python3

# Take a file and of descriptions, multi-line and separated by blank lines,
# and turn it into a collection of GPX waypoints
# suitable for import into Osmand, PyTopo or other mapping programs.
# Copyright 2013 by Akkana Peck <akkana@shallowsky.com>.
# Please share and enjoy under the GPL v2 or later.

import sys, os
import re
import html
import datetime
import time

# import googlemaps   # need this for exceptions
# from googlemaps import GoogleMaps
import urllib.request, urllib.parse, urllib.error, json

def write_gpx_file(entries, filename, omit_address=False, omit_time=False):
    """Write the list of entries -- each entry is [lat, long, desc] --
       to a GPX file as separate waypoints.
    """
    fp = open(filename, 'w')
    fp.write('''<?xml version="1.0" encoding="UTF-8"?>
<gpx
 version="1.0"
creator="waymaker v. 0.2"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns="http://www.topografix.com/GPX/1/0"
xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
''')
    if not omit_time:
        fp.write('<time>%s</time>\n' % datetime.datetime.now().isoformat())

    # Calculate our bounds:
    minlat = 91
    maxlat = -90
    minlon = 1000
    maxlon = -1000
    for ent in entries:
        if ent[0] < minlat:
            minlat = ent[0]
        if ent[0] > maxlat:
            maxlat = ent[0]
        if ent[1] < minlon:
            minlon = ent[1]
        if ent[1] > maxlon:
            maxlon = ent[1]

    fp.write('<bounds minlat="%f" minlon="%f" maxlat="%f" maxlon="%f"/>\n' \
                 % (minlat, minlon, maxlat, maxlon))

    for ent in entries:
        print('<wpt lat="%f" lon="%f">' % (ent[0], ent[1]), file=fp)
        if omit_address:
            addy = '\n'.join(ent[2].split('\n')[2:])
        else:
            addy = ent[2]
        print('<name>%s</name>' % addy, file=fp)
        print('</wpt>', file=fp)

    fp.write('</gpx>\n')
    fp.close()

#
# Options for geocoding:
#
# The US Census offers an excellent API and even offers batch geocoding:
# https://www.census.gov/programs-surveys/geography/technical-documentation/complete-technical-documentation/census-geocoder.html
# You can use it interactively too:
# https://geocoding.geo.census.gov/geocoder/
#
# If something goes wrong with that, the USPS has made their API free
# but it requires registration:
# https://www.usps.com/business/web-tools-apis/#dev
# https://www.usps.com/business/web-tools-apis/address-information-api.htm
#
# Google Maps here used to offer a geocoding API, but it became
# increasingly restrictive and then stopped working entirely.
#

def geocode(addr):
    """Geocode using the US Census API.
       Returns a (lat, lon) pair, or None, None.
    """
    url = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress'
    url += '?benchmark=Public_AR_Current'
    url += '&vintage=Current'
    url += '&format=json'
    url += '&address=' + urllib.parse.quote_plus(addr)

    data = str(urllib.request.urlopen(url).read(), 'utf-8')
    dataj = json.loads(data)

    if not dataj['result']['addressMatches']:
        return None, None

    firstmatch = dataj['result']['addressMatches'][0]

    # Weirdly, they call the coordinates x and y, not longitude/latitude
    return (float(firstmatch['coordinates']['y']),
            float(firstmatch['coordinates']['x']))

def read_description_file(filename):
    """Read a file filled with multi-line descriptions, blank line separated.
       The first line of each description may be latitude and longitude,
       separated by whitespace.
       The next one or two lines should be a US street address,
       including zip code.
       The rest is free-form description.
       Returns a list of entries, where each entry is a list:
       [ latitude, longitude, text ]
    """

    entries = []
    cur_ent = []

    fp = open(filename)
    for line in fp:
        line = line.strip()
        if not line:    # end of a record. Save the current entry and move on
            if cur_ent:
                entries.append(cur_ent)
                cur_ent = []
            continue

        if not cur_ent:
            numeric = '[\+\-\d\.]'
            # re.search doesn't work if you put the % expression in the
            # search call, but it does work if you store the
            # intermediate string first:
            twonums = '^(%s+)\s+(%s+)$' % (numeric, numeric)
            match = re.search(twonums, line)
            if match:
                # Okay, they may be numbers, but that doesn't mean
                # they're coordinates. Consider 23054 7250 Rd.
                # So let's do a sanity check:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if lat >= -90 and lat <= 90 and lon >= -180 and lon <= 360:
                    cur_ent.append(lat)
                    cur_ent.append(lon)
                    # Start cur_ent[2] with a null string:
                    cur_ent.append('')
                    continue
                # If the numbers didn't pass the sanity check,
                # fall through to the address parser.

            # Now either the first line, or the first two lines,
            # are an address. But we should be able to tell them apart:
            # The last two fields of an address are a state
            # (2 uppercase letters) followed by a 5-digit zip code.
            statezip = '.*[A-Z]{2}\s+\d{5}$'
            match = re.search(statezip, line)
            # If the state/zip wasn't in the first line, try the second:
            line2 = None
            if not match:
                # Try guards against StopIteration, i.e. end of file
                try:
                    line2 = next(fp).strip()
                    if not line2:
                        # a blank line here means the previous line
                        # wasn't meant to be the start of an entry anyway --
                        # probably just a stray URL or something.
                        continue
                    match = re.search(statezip, line2)
                    if not match:
                        print("Couldn't find coordinates OR address in '%s' or in '%s'" % (line, line2))
                        print("Skipping this entry")
                        while True:
                            line = next(fp).strip()
                            if not line:
                                break
                        # Now continue the outer loop --
                        # don't try to process this blank line as an address.
                        continue
                except StopIteration:
                    # StopIteration means the end of the file.
                    # Since this clause is only to start a new entry,
                    # that means we can return without doing any cleanup
                    # except closing the file.
                    # (montrose.txt is a good test case --
                    # or anything that ends with a blank line.)
                    # print("StopIteration")
                    fp.close()
                    return entries

            # There's a match! Either single or double line.
            # Either way, look it up and add it to the desc.
            addr = line
            if line2:
                addr += ' ' + line2
            print("Found an address! %s" % addr)

            # So instead, use a local version:
            lat, lon = geocode(addr)
            if not lat:
                cur_ent = []
                continue

            cur_ent.append(lat)
            cur_ent.append(lon)

            # XXX Need to remove special characters XML can't handle:
            # ? & ( ) ' "

            # and append the address as the first part of the description:
            if line2:
                cur_ent.append(html.escape(line) + '\n' + html.escape(line2))
            else:
                cur_ent.append(html.escape(line))

            continue

        # Else we have a non-null line AND we have a current entry,
        # so we're just appending to cur_ent[2].
        # But skip lines that have any long words that are likely
        # too long to wrap on a phone display (they're probably URLs).
        if re.search('\S{27,}', line):
            print("Skipping long line: '%s'" % line)
            continue
        if cur_ent[2]:
            cur_ent[2] += '\n' + html.escape(line)
        else:
            cur_ent[2] += html.escape(line)

    if cur_ent:
        entries.append(cur_ent)

    fp.close()

    return entries

def Usage():
        print("Usage: %s infile.txt outfile.gpx"
              % os.path.basename(sys.argv[0]))
        sys.exit(1)

if __name__ == "__main__" :
    if len(sys.argv) < 3:
        Usage()

    # It would be relatively easy to mess up with autocomplete and
    # run waymaker foo.txt foo.txt. That would be bad.
    if not(sys.argv[2].endswith('.gpx')):
        print("Output file %s doesn't end with .gpx" % sys.argv[2])
        Usage()

    entries = read_description_file(sys.argv[1])
    write_gpx_file(entries, sys.argv[2])

