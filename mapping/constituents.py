#!/usr/bin/env python3

"""Given an input spreadsheet of members with addresses,
   and a set of geojson files for districts (e.g. state senate districts),
   produce an output spreadsheet that includes each member's districts.
"""

from collections import defaultdict
# from urllib.parse import unquote_plus, quote_plus
import urllib.parse, urllib.request
import json
import re
import sys, os

from shapely.geometry import Point, Polygon


# Nominatim is failing on about 2/3 of New Mexico addresses I give it.
# Use the census instead: https://geocoding.geo.census.gov/geocoder/
# GEOLOCATOR can be "Nominatim" or "USCensus"
# though Nominatim has been failing and probably isn't worth using.
# I never got any of the other geopy geocoders to work either,
# even after registering.
GEOLOCATOR = "USCensus"
USE_NOMINATIM = False
USE_CENSUS = True

if GEOLOCATOR == "Nominatim":
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter

    Geolocator = Nominatim(user_agent="constituents")


# Called as a CGI?
if 'REQUEST_METHOD' in os.environ:
    print("Content-Type: text/plain\n\n")


def census_geocode(addr):
    """Geocode using the US Census API.
       Returns (lat, lon), or None, None.
    """
    url = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress'
    url += '?benchmark=Public_AR_Current'
    url += '&vintage=Current'
    url += '&format=json'
    url += '&address=' + urllib.parse.quote_plus(addr)
    # print("url:", url)

    data = str(urllib.request.urlopen(url).read(), 'utf-8')
    dataj = json.loads(data)

    if not dataj['result']['addressMatches']:
        return None, None

    firstmatch = dataj['result']['addressMatches'][0]

    # Weirdly, they call the coordinates x and y, not longitude/latitude
    return (float(firstmatch['coordinates']['y']),
            float(firstmatch['coordinates']['x']))


# Nominatim requires local caching, the Census doesn't;
# but it's a good idea regardless of the geocoder being used.
if 'REQUEST_METHOD' in os.environ:    # running as a CGI
    CACHEFILE = os.path.expanduser("constituents-cache.json")
else:                                 # running locallyq
    CACHEFILE = os.path.expanduser("~/.cache/constituents/constituents-cache.json")

Cachedata = {}

if os.path.exists(CACHEFILE):
    print(CACHEFILE, "exists", file=sys.stderr)
    try:
        with open(CACHEFILE) as fp:
            Cachedata = json.load(fp)
            print("Read cached data from", CACHEFILE,
                  ":", len(Cachedata), "items", file=sys.stderr)
    except:
        print("Couldn't read JSON from cache file", CACHEFILE, file=sys.stderr)
else:
    print("'%s' doesn't exist" % CACHEFILE, file=sys.stderr)
    try:
        os.makedirs(os.path.dirname(CACHEFILE))
    except FileExistsError as e:
        pass
    except Exception as e:    # Most likely a PermissionError
        print("Couldn't create", CACHEFILE, ":", e, file=sys.stderr)


# Some patterns for things Nominatim can't handle
BAD_ADDR_PATTERNS = [
    r"(PO )?[bB]ox *\#* *[0-9]+,? *"
]
PATTERNS_TO_REMOVE = [
    r"\# *[0-9]+ *"
]

def clean_addr(addr):
    """First remove things like apartment numbers and PO boxes,
       which Nominatim can't handle. The Census geolocator is more tolerant.
    """
    for pat in BAD_ADDR_PATTERNS:
        if re.match(pat, addr):
            Cachedata[addr] = (None, None)
            print(addr, ": bad address, can't geolocate")
            return None

    for pat in PATTERNS_TO_REMOVE:
        addr = re.sub(pat, "", addr)

    return addr


def geocode(addr):
    """Geocode a single address using GeoPY/Nominatim.
       Returns a (lat, lon) pair, or None, None.
    """
    constituents = defaultdict(list)

    if addr in Cachedata:
        # print(addr, "was cached: returning", Cachedata[addr], file=sys.stderr)
        return Cachedata[addr]

    # print("geocode '%s'" % addr, file=sys.stderr)

    # print(".", end="")
    # sys.stdout.flush()

    if GEOLOCATOR == "Nominatim":
        location = Geocode(addr)
        if not location:
            Cachedata[addr] = (None, None)
            return Cachedata[addr]

        # Nominatim returns a tuple of number, street, city, county,state, zip,
        # (lat, lon)
        Cachedata[addr] = location[-1]
        return Cachedata[addr]

    elif GEOLOCATOR == "USCensus":
        Cachedata[addr] = census_geocode(addr)
        return Cachedata[addr]


def load_geojson(geojson_file):
    with open(geojson_file, 'rb') as fp:
        district_json = json.load(fp)
        district_polygons = {}
        for feature in district_json['features']:
            district_polygons[feature["properties"]["DIST"]] = \
                Polygon(feature['geometry']['coordinates'][0])

        # Done with json
        district_json = None
    # print("Found", len(district_polygons), "districts in", geojson_file,
    #       file=sys.stderr)
    return district_polygons


def district_sort_key(k):
    if type(k) is int:
        return "%03d" % k
    return "%03s" % k


def handle_address(addrline, district_polygons):
    addrline = addrline.strip()
    try:
        lat, lon = geocode(addrline)
    except:
        lat = None
        lon = None
    if not lat or not lon:
        # print("Couldn't geocode", addrline)
        constituents["address error"].append(addrline)
        return

    pt = Point(lon, lat)

    for district in district_polygons:
        # print("checking district", district)
        if pt.within(district_polygons[district]):
            constituents[district].append(addrline)
            break
    else:
        constituents["unknown"].append(addrline)


def districts_for_addresses(addressfile, district_json):
    district_polygons = load_geojson(district_json)

    with open(addressfile) as fp:
        for addrline in fp:
            handle_address(addrline, district_polygons)

    # print("Saving", len(Cachedata), "items to cache")
    with open(CACHEFILE, 'w') as fp:
        json.dump(Cachedata, fp, indent=2)

    return constituents


def districts_for_csv(csvfile, polygon_files):
    import csv

    polygon_sets = {}
    for pf in polygon_files:
        polygon_sets[os.path.basename(pf)] = load_geojson(pf)

    allrows = []

    # The keys to save
    savekeys = [ 'name', 'address', 'latitude', 'longitude' ]
    polyfilekeys = [ os.path.splitext(f)[0] for f in polygon_files ]

    with open(csvfile) as csvfp:
        reader = csv.DictReader(csvfp)
        for row in reader:
            # Each row is an OrderedDict
            # fields needed: Account Name, Email, Mailing Street,
            # Mailing City, Mailing State/Province, Mailing Zip/Postal Code

            if not row['Mailing Street'].strip():
               print(row['Account Name'], "has no address, skipping",
                     file=sys.stderr)
               continue
            # Nominatim can't handle 9-digit zip codes, returns None
            # for any address that includes one
            zip = row['Mailing Zip/Postal Code']
            # if '-' in zip:
            #     zip = zip.split('-')[0]
            addr = "%s, %s, %s %s" % (
                row['Mailing Street'].strip(), row['Mailing City'].strip(),
                row['Mailing State/Province'].strip(), zip)
            if addr.startswith("PO Box"):
                print(row['Account Name'], "is a PO Box, skipping",
                      file=sys.stderr)
                continue

            addr = clean_addr(addr)

            # Mark it for saving even before knowing if it's geocodable.
            # We can still add to the object, which won't be
            # actually written to the cache file til the end.
            member = {
                'name': row['Account Name'],
                'address': addr,
                'latitude': 0,
                'longitude': 0,
            }
            for key in polyfilekeys:
                member[key] = ''
            allrows.append(member)

            try:
                gc = geocode(addr)
                lat, lon = gc
            except RuntimeError as e:
                print("Couldn't geocode", addr, ":", e, file=sys.stderr)
                # for polyset in polygon_sets:
                #     constituents[polyset] = None
                continue

            if not lat or not lon:
                print("Error geocoding", row['Account Name'], "at:", addr,
                      file=sys.stderr)
                row['latitude'] = ''
                row['longitude'] = ''
                continue

            member['latitude'] = lat
            member['longitude'] = lon

            # We have coordinates.
            pt = Point(lon, lat)
            for polyset in polygon_sets:  # chambers, e.g. House, Senate
                polysetkey = os.path.splitext(polyset)[0]
                for district in polygon_sets[polyset]:
                    if pt.within(polygon_sets[polyset][district]):
                        member[polysetkey] = district
                        break

    # print("Saving", len(Cachedata), "items to cache")
    with open(CACHEFILE, 'w') as fp:
        json.dump(Cachedata, fp, indent=2)

    # Save as both JSON and CSV
    outfilebase = "districts-%s" % os.path.splitext(csvfile)[0]
    with open(outfilebase + ".json", 'w') as fp:
        json.dump(allrows, fp, indent=2)
        print("Saved as", outfilebase + ".json", file=sys.stderr)

    # print("Will save CSV with keys:", savekeys, '+', polyfilekeys)
    with open(outfilebase + ".csv", 'w') as fp:
        writer = csv.DictWriter(fp, fieldnames=savekeys + polyfilekeys,
                                lineterminator='\n')
        writer.writeheader()
        for row in allrows:
            writer.writerow(row)
        print("Saved as", outfilebase + ".csv", file=sys.stderr)

    return allrows


if __name__ == '__main__':
    # Called as a CGI?
    if 'REQUEST_METHOD' in os.environ:
        district_polygons = load_geojson(
            "../../districtmaps/data/NM_Senate.json")
        import cgi
        form = cgi.FieldStorage()
        if 'addresses' in form:
            addresses = urllib.parse.unquote_plus(form["addresses"].value)
            for addrline in addresses.splitlines():
                handle_address(addrline, district_polygons)

            for dist in sorted(constituents.keys(), key=district_sort_key):
                print("\nDistrict", dist)
                if constituents[dist]:
                    for addr in constituents[dist]:
                        print("   ", addr)
                else:
                    print("    No constituents")
            sys.exit(0)

    # Not a CGI
    if sys.argv[1].endswith('.csv'):
        try:
            constituents = districts_for_csv(sys.argv[1], sys.argv[2:])
        except KeyboardInterrupt:
            print("Interrupt")
            sys.exit(0)
    elif sys.argv[1].endswith('.xlsx'):
        print("Sorry, can't read xlsx, please convert it to CSV",
              file=sys.stderr)
        sys.exit(1)
    else:
        constituents = districts_for_addresses(sys.argv[1], sys.argv[2])
