#!/usr/bin/env python3

"""Given an input spreadsheet of members with addresses,
   and a set of geojson files for districts (e.g. state senate districts),
   produce an output spreadsheet that includes each member's districts.
"""

from collections import defaultdict
from urllib.parse import unquote_plus
import json
from simplejson.errors import JSONDecodeError
from shapely.geometry import Point, Polygon
from geopy.geocoders import Nominatim, PickPoint
from geopy.extra.rate_limiter import RateLimiter
import requests
import argparse
import traceback
import csv
import re
import sys, os


# Nominatim requires local caching.
# CACHEFILE = os.path.expanduser("~/.config/constituents/constituents-cache.json")
CACHEFILE = "constituents-cache.json"

# Cached addresses, saved in CACHEFILE
Cachedata = {}

# When initialized, will store the function to use when geocoding.
Geocode = None


# Some patterns for things Nominatim can't handle
BAD_ADDR_PATTERNS = [
    "(PO )?[bB]ox *\#* *[0-9]+,? *"
]
PATTERNS_TO_REMOVE = [
    "\# *[0-9]+ *"
]


def geocode_US_census(addr):
    """Geocode using the US Census API"""
    url = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=%s&benchmark=2020&format=json' % addr.replace(' ', '+')
    try:
        req = requests.get(url)
        output = req.json()
        # print("Got JSON:", output)
        matches = output["result"]["addressMatches"]
        if len(matches) == 0:
            print("Couldn't match", addr)
            return [ (None, None) ]

        if len(matches) > 1:
            print("Yikes, more than one match for", addr)
            for match in matches:
                print("   ", match, ":", match["coordinates"])
        # print('coordinates:', matches[0]["coordinates"])

        # To be consistent with geopy, should return a tuple of
        # number, street, city, county,state, zip, (lat, lon)
        # but nothing except the final tuple is used, so
        # for now, that's enough. (Census doesn't differentiate number.)
        match = matches[0]
        return [ ( match["coordinates"]["y"],
                   match["coordinates"]["x"] ) ]

    except JSONDecodeError as e:
        # When this happens it can't print req.text either,
        print("JSON decode error on: '%s'" % req.text)
        return [ (None, None) ]
    except Exception as e:
        print("Exception: '%s' geolocating '%s'" % (e, addr))
        traceback.print_exc(file=sys.stderr)
        return [ (None, None) ]


def init_geolocator():
    global Geocode, Cachedata

    # geocoding API investigation:
    # US Census!
    # https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html
    # e.g. https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=123+Main+Street,+Las+Cruces,+NM+88007-8816&benchmark=2020&format=json
    #
    # Nominatim: randomly stops serving anything, giving only timeouts
    #   (even when used on only one address or with rate limiter)
    # Pelias: doesn't seem to understand searching for addresses,
    #   gives a list of results most of which aren't near the specified city
    #   even with sources=oa which is supposed to search for addresses
    # OpenCageData: gives two results one of which is a completely different
    #   address than the one asked for
    #
    # Services that you can't even try without registering:
    # PickPoint: Has free tier, but fails on about 1/3 of US addresses
    # Google: wants a credit card, claims it won't charge it if you
    #   don't make too many queries (but no way to check or limit that)
    # geonames.org: their examples use an account named "demo"
    #   but you can't actually use that for testing
    # mapbox.com
    # here.com
    # developer.what3words.com
    # developer.tomtom.com
    # smarty.com
    # mapquest.com: they have an example at
    # https://developer.mapquest.com/documentation/samples/geocoding/v1/address
    # but it doesn't actually do anything, just stays on the default query.
    # OpenMapQuest (https://developer.mapquest.com/documentation/open/):
    # intro page doesn't even load, just spins a busy indicator forever.
    #
    # Services that don't work via geopy:
    # Don't work without an API key:
    # www.geocod.io/docs/: the "try this in your browser right now"
    #   links don't work since they use api_key=YOUR_API_KEY
    # USPS: does address validation but not geolocation
    # https://geocoding.geo.census.gov/geocoder/

    pickpointapikey = os.getenv("PICKPOINTAPIKEY")
    if True:
        # Use the Census API
        Geocode = geocode_US_census
        print("Geolocation using the US Census API")

    elif pickpointapikey:
        # https://geopy.readthedocs.io/en/latest/#geopy.geocoders.PickPoint
        Geocode = PickPoint(pickpointapikey).geocode
        print("Geolocation courtesy of PickPoint.io")

    elif False:
        # Use the free Nominatim service, though it doesn't always work
        # even with the rate limiter in place.

        Geolocator = Nominatim(user_agent="constituents")

        # Nominatim has a limit of 1 request per second for free non-OSM use.
        # (They don't always enforce this, but be nice and follow the guidelines!)
        # Unfortunately, even when rate limited, Nominatim will randomly
        # start timing out or raising errors like
        # geopy.exc.GeocoderUnavailable: HTTPSConnectionPool(host='nominatim.openstreetmap.org', port=443): Max retries exceeded with url: /search?q=111+N+California+Ave%2C+Silver+City%2C+NM+88061-3720&format=json&limit=1 (Caused by ReadTimeoutError("HTTPSConnectionPool(host='nominatim.openstreetmap.org', port=443): Read timed out. (read timeout=1)"))
        Geocode = RateLimiter(Geolocator.geocode, min_delay_seconds=1)
        print("Geolocation courtesy of OpenStreetMap/Nominatim")
        print()


    # Set up a cache
    if os.path.exists(CACHEFILE):
        print(CACHEFILE, "exists", file=sys.stderr)
        try:
            with open(CACHEFILE) as fp:
                Cachedata = json.load(fp)
                print("Read cached data from", CACHEFILE, file=sys.stderr)
        except:
            print("Couldn't read JSON from cache file", CACHEFILE,
                  file=sys.stderr)
    else:
        print("'%s' doesn't exist" % CACHEFILE, file=sys.stderr)
        try:
            os.makedirs(os.path.dirname(CACHEFILE))
        except FileExistsError as e:
            pass
        except Exception as e:    # Most likely a PermissionError
            print("Couldn't create", os.path.dirname(CACHEFILE),
                  ":", e, file=sys.stderr)


def clean_addr(addr):
    """First remove things like apartment numbers and PO boxes,
       which Nominatim can't handle
    """
    for pat in BAD_ADDR_PATTERNS:
        if re.match(pat, addr):
            Cachedata[addr] = (None, None)
            print(addr, ": bad address, can't geolocate")
            return None

    for pat in PATTERNS_TO_REMOVE:
        addr = re.sub(pat, "", addr)

    return addr


def geocode(addr, ignore_cache=False):
    """Geocode a single address using GeoPY.
       Returns a (lat, lon) pair, or None, None.
    """
    print("*** geocode '%s'" % addr, file=sys.stderr)

    if addr in Cachedata and not ignore_cache:
        print(addr, "was cached: returning", Cachedata[addr], file=sys.stderr)
        return Cachedata[addr]

    print("Not cached", file=sys.stderr)
    print(".", end="")
    sys.stdout.flush()

    location = Geocode(addr)
    if not location:
        print("Couldn't geocode", addr)
        Cachedata[addr] = (None, None)
        return Cachedata[addr]

    print("geocoded:", location[-1])

    # Nominatim returns a tuple of number, street, city, county,state, zip,
    # (lat, lon)
    Cachedata[addr] = location[-1]
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
    print("Found", len(district_polygons), "districts in", geojson_file,
          file=sys.stderr)
    return district_polygons


def district_sort_key(k):
    if type(k) is int:
        return "%03d" % k
    return "%03s" % k


def save_cachefile():
    print("Saving cachefile with", len(Cachedata), "entries")

    with open(CACHEFILE, 'w') as fp:
        json.dump(Cachedata, fp, indent=2)


def read_csv(inputcsv):
    print("Reading CSV file", inputcsv)
    # Read everyone in from the inputcsv to members
    members = []
    with open(inputcsv) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            print(row)
            # Fields we care about: "League: League Name", "First Name".
            # "Last Name", "Mailing Street", "Mailing City",
            # "Mailing State/Province" "Mailing Country",
            # "Mailing Zip/Postal Code"

            # Only care about NM, US
            if row["Mailing Country"] != "US":
                print("Skipping", row["First Name"], row["Last Name"],
                      ":",  row["Mailing Country"], "not US", file=sys.stderr)
                continue
            if row["Mailing State/Province"] != "NM":
                print("Skipping", row["First Name"], row["Last Name"],
                      ":",  row["Mailing State/Province"], "not NM",
                      file=sys.stderr)
                continue

            # Some members don't list an address at all
            if not row["Mailing Street"] or not row["Mailing City"]:
                print("Skipping", row["First Name"], row["Last Name"],
                      ": Missing street address or city",
                      file=sys.stderr)
                continue

            addr = "%s, %s, NM %s" % (row["Mailing Street"],
                                      row["Mailing City"],
                                      row["Mailing Zip/Postal Code"])

            member = {
                "addr": addr,
                "lastname": row["Last Name"],
                "firstname": row["First Name"],
                "leaguename": row["League: League Name"]
            }
            members.append(member)

    return members


def whichdistrict(point, polygons):
    """If point is inside any of the polygons, return the associated district,
       else None.
    """
    for district in polygons:
        # print("checking district", district)
        if point.within(polygons[district]):
            return district
    return None


def districts_for_csv(csvfile, districtfiles, naddrs=0):
    members = read_csv(csvfile)

    # Now all the members in the CSV have been read in to members
    print("Read", len(members), "members")

    num_addrs_done = 0
    for m in members:
        if "clean_addr" not in members:
            m["clean_addr"] = clean_addr(m["addr"])
        if not m["clean_addr"]:
            # It might be ungeolocatable, e.g. a PO Box
            continue
        if m["clean_addr"] in Cachedata:
            m["lat"], m["lon"] = Cachedata[m["clean_addr"]]
        elif m["clean_addr"]:
            print(m["clean_addr"], "is not in Cachedata; geocoding")
            m["lat"], m["lon"] = geocode(m["clean_addr"])
            print(m["addr"], "-->", m["lat"], m["lon"])
            num_addrs_done += 1
            if naddrs and num_addrs_done > naddrs:
                break

    # Make sure all coordinates are cached before proceding
    save_cachefile()

    print()
    print("****** looking for districts")
    print()

    # Now figure out districts for the members who have lat/lon.
    csv_fieldnames = [ "firstname", "lastname", "leaguename", "addr" ]
    csv_districtnames = []
    for districtfile in districtfiles:
        districttype, ext = os.path.splitext(districtfile)
        csv_districtnames.append(districttype)
        district_polygons = load_geojson(districtfile)
        print("Loaded", districtfile)
        print()

        for m in members:
            if "lat" not in m or "lon" not in m or not m["lat"] or not m["lon"]:
                # print("No coordinates for", m["firstname"], m["lastname"])
                continue

            pt = Point(m["lon"], m["lat"])
            if "districts" not in m:
                m["districts"] = {}
            m["districts"][districttype] = whichdistrict(pt, district_polygons)
            # print("  ", m["firstname"], m["lastname"], m["addr"],
            #       districtfile, "districts:", m["districts"])

    with open("member-districts.json", "w") as fp:
        json.dump(members, fp, indent=2)
        print("Saved to member-districts.json")

    with open("member-districts.csv", "w") as fp:
        csvwriter = csv.writer(fp)
        csvwriter.writerow(csv_fieldnames + csv_districtnames)
        for m in members:
            if "districts" in m:
                row = [ m[field] for field in csv_fieldnames ]
                for distname in csv_districtnames:
                    if distname in m["districts"]:
                        row.append(m["districts"][distname])
                    else:
                        row.append("")
                csvwriter.writerow(row)
        print("Saved to member-districts.csv")


def tryagain():
    """Retry any address that has cached coordinates of None, None"""
    changes = False
    for addr in Cachedata:
        for pat in BAD_ADDR_PATTERNS:
            if re.match(pat, addr):
                print("Skipping", addr)
                addr = None
                break
        if not addr:
            continue

        if not Cachedata[addr][0] or not Cachedata[addr][1]:
            print("Retrying", addr)
            foo = geocode(addr, ignore_cache=True)
            print("geocode", addr, "returned", foo)
            lat, lon = foo
            if lat and lon:
                changes = True

    if changes:
        print("There were changes", end="")
        save_cachefile()


if __name__ == '__main__':
    # Check arguments
    print("Parsing arguments ...")
    parser = argparse.ArgumentParser(description="Map addresses to districts")
    parser.add_argument('-n', action="store", default=0, dest="naddrs",
                        type=int, help='How many addresses to process.')
    parser.add_argument('--tryagain', dest="tryagain", default=False,
                        action="store_true",
        help="Try again to get addresses that aren't already geocoded")
    parser.add_argument('inputcsv', nargs=1, help="Input CSV file")
    parser.add_argument('distfiles', nargs='+', help="district files (geojson)")
    args = parser.parse_args()
    print("args:", args)

    for districtfile in args.distfiles:
        if not (districtfile.endswith(".json")
                or districtfile.endswith(".geojson")):
            parser.print_help()
            sys.exit(1)

    init_geolocator()
    print("Initially Cachedata has", len(Cachedata), "entries")

    if args.tryagain:
        tryagain()

    # Argparse sets inputcsv as a list even though it's nargs=1
    districts_for_csv(args.inputcsv[0], args.distfiles, args.naddrs)

