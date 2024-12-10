#!/usr/bin/env python3

# Take a file of descriptions, multi-line and separated by blank lines,
# 
# suitable for import into Osmand, PyTopo or other mapping programs.
# Copyright 2013 by Akkana Peck <akkana@shallowsky.com>.
# Please share and enjoy under the GPL v2 or later.

"""waymaker: take a file of names and descriptions
   and turn it into a collection of GPX waypoints.

   file format: (may or may not have lat/lon already, or zip code)

latitude longitude
street address
city, state zip
comments comments
more comments

street address
city, state
comments comments

    May or may not have lat/lon already; if it does, it should be first.
    Zip code may be missing.

"""

import sys, os
import re
import html
import datetime
import time

import urllib.request, urllib.parse, urllib.error, json


def write_gpx_file(entries, filename, omit_address=False, omit_time=False):
    """Write the list of entries -- each entry is a dic with keys
       coords, addr, desc
       to a GPX file as separate waypoints.
       entries is a list of (lat, lon, address-and-other-stuff)
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

    # Calculate bounds:
    minlat = 91
    maxlat = -90
    minlon = 1000
    maxlon = -1000
    for ent in entries:
        if "coords" not in ent:
            continue
        if ent["coords"][0] < minlat:
            minlat = ent["coords"][0]
        if ent["coords"][0] > maxlat:
            maxlat = ent["coords"][0]
        if ent["coords"][1] < minlon:
            minlon = ent["coords"][1]
        if ent["coords"][1] > maxlon:
            maxlon = ent["coords"][1]

    fp.write('<bounds minlat="%f" minlon="%f" maxlat="%f" maxlon="%f"/>\n' \
                 % (minlat, minlon, maxlat, maxlon))

    for ent in entries:
        print('<wpt lat="%f" lon="%f">' % (ent["coords"][0], ent["coords"][1]),
              file=fp)
        if omit_address:
            addy = '\n'.join(ent["addr"].split('\n')[2:])
        else:
            addy = ent["addr"]
        if "desc" in ent:
            addy += '\n' + ent["desc"]

        # XXX Need to remove special characters XML can't handle:
        # ? & ( ) ' "
        addy = html.escape(addy)

        print('<name>%s</name>' % addy, file=fp)
        print('</wpt>', file=fp)

    fp.write('</gpx>\n')
    fp.close()


def write_text_file(entries, filename):
    with open(filename, 'w') as fp:
        for ent in entries:
            if "coords" in ent:
                print(f"{ent['coords'][0]} {ent['coords'][1]}", file=fp)
            print(ent["addr"], file=fp)
            if "desc" in ent:
                print(ent["desc"], file=fp)
            print('', file=fp)


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
# Two other options not yet included here:
# Geocoder: https://geocoder.readthedocs.io/
# GeoPy:    https://geopy.readthedocs.io/en/latest/#geocodeearth
#

def geocode(addr):
    """Geocode using the US Census API.
       Returns (lat, lon, zip), or None, None, None.
    """
    print("Geocoding", addr)

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
            float(firstmatch['coordinates']['x']),
            firstmatch['addressComponents']['zip'])


# Useful patterns
# stateend = '.*\s+([A-Z]{2})$'
statezip = r'.*\s+([A-Z]{2})\s*(\d{5})?.*$'
numeric = r'[\+\-\d\.]'
twonums = r'^(%s+)\s+(%s+)$' % (numeric, numeric)

# street directions that could be confused for a state name
abqdirections = [ "NE", "NW", "SE", "SW" ]

def read_description_file(filename):
    """Read a file filled with multi-line descriptions, blank line separated.
       The first line of each description may be latitude and longitude,
       separated by whitespace.
       The next one or two lines should be a US street address,
       including zip code.
       The rest is free-form description.
       Returns a list of entries, where each entry is a dict
       with keys: coordinates, addr, desc

       Save a modified file to filename-coords
    """

    entries = []
    cur_ent = {}

    fp = open(filename)
    for origline in fp:
        line = origline.strip()
        if not line:    # end of a record. Save the current entry and move on
            if cur_ent:
                entries.append(cur_ent)
                cur_ent = {}
            continue

        line = re.sub('#.*$', '', line).strip()
        if not line:
            # Lines with only comments get skipped,
            # but don't trigger a new entry
            continue

        if not cur_ent or "addr" not in cur_ent or not cur_ent["addr"]:
            # re.search doesn't work if you put the % expression in the
            # search call, but it does work if you store the
            # intermediate string first:
            match = re.search(twonums, line)
            if match:
                # Okay, they may be numbers, but that doesn't mean
                # they're coordinates. Consider 23054 7250 Rd.
                # So let's do a sanity check:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if lat >= -90 and lat <= 90 and lon >= -180 and lon <= 360:
                    cur_ent["coords"] = lat, lon
                    # go to the next line
                    continue
                # If the numbers didn't pass the sanity check,
                # fall through to the address parser.

            # Now either the first line, or the first two lines,
            # are an address. But we should be able to tell them apart:
            # The last two fields of an address are a state
            # (2 uppercase letters), maybe followed by a 5-digit zip code.
            match = re.search(statezip, line)
            # Albuquerque street addresses often end in NE, SW etc.
            # which match the state pattern but aren't states.
            if match and match.group(1):
                state = match.group(1)
                if state in abqdirections:
                    match = None
            # If the state/zip wasn't in the first line, try the second:
            line2 = None
            if match and match.group(2):
                # If we've seen a zip code, no need to look for further addr
                has_zip = match.group(2)
            else:
                has_zip = None
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
                    else:
                        has_zip = match.group(2)
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
            print("\nFound an address! %s" % addr)

            # Were there already coordinates?
            if "coords" not in cur_ent or not cur_ent["coords"]:
                lat, lon, zip = geocode(addr)
                if not lat:
                    print("Can't geocode", addr)
                    cur_ent = {}
                    continue
            else:
                print(addr, "Already has coordinates")

            if not has_zip:
                addr += " " + zip

            cur_ent["addr"] = addr
            cur_ent["coords"] = (lat, lon)

            continue

        # Else we have a non-null line AND we have a current entry,
        # so we're just appending to the description..
        # But skip lines that have any long words that are likely
        # too long to wrap on a phone display (they're probably URLs).
        if re.search(r'\S{27,}', line):
            print("Skipping long line: '%s'" % line)
            continue
        if "desc" in cur_ent and cur_ent["desc"]:
            cur_ent["desc"] += '\n' + line
        else:
            cur_ent["desc"] = line

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
    print()

    write_gpx_file(entries, sys.argv[2])
    print("Wrote GPX file", sys.argv[2])

    base, ext = os.path.splitext(sys.argv[2])
    textfile = base + ".txt"
    # Don't overwrite the input file, since write_text_file
    # doesn't preserve comments and other formatting
    if textfile == sys.argv[1]:
        textfile = base + "1.txt"
    write_text_file(entries, textfile)
    print("Saved text file", textfile)

