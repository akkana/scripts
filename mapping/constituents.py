#!/usr/bin/env python3

from collections import defaultdict
from urllib.parse import unquote_plus
import json
from shapely.geometry import Point, Polygon
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import sys, os


# Called as a CGI?
if 'REQUEST_METHOD' in os.environ:
    print("Content-Type: text/plain\n\n")


Geolocator = Nominatim(user_agent="constituents")

# Nominatim has a limit of 1 request per second for free non-OSM use.
# (They don't always enforce this, but be nice and follow the guidelines!)
Geocode = RateLimiter(Geolocator.geocode, min_delay_seconds=1)
print("Geolocation courtesy of OpenStreetMap/Nominatim")
if 'REQUEST_METHOD' not in os.environ:
    print("Warning: rate limiting new addresses to 1 per second.")
    print("For faster bulk queries, consider using OpenMapQuest or PickPoint")
    print("(see https://geopy.readthedocs.io/en/latest/#geopy-is-not-a-service)")
print()

# Nominatim also requires local caching.
if 'REQUEST_METHOD' in os.environ:
    CACHEFILE = os.path.expanduser("constituents-cache.json")
else:
    CACHEFILE = os.path.expanduser("~/.config/constituents/constituents-cache.json")

Cachedata = {}

if os.path.exists(CACHEFILE):
    print(CACHEFILE, "exists", file=sys.stderr)
    try:
        with open(CACHEFILE) as fp:
            Cachedata = json.load(fp)
            print("Read cached data from", CACHEFILE, file=sys.stderr)
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


constituents = defaultdict(list)


def geocode(addr):
    """Geocode a single address using GeoPY/Nominatim.
       Returns a (lat, lon) pair, or None, None.
    """
    print("geocode '%s'" % addr, file=sys.stderr)
    if addr in Cachedata:
        print(addr, "was cached: returning", Cachedata[addr], file=sys.stderr)
        return Cachedata[addr]

    print("Not cached", file=sys.stderr)
    print(".", end="")
    sys.stdout.flush()

    location = Geocode(addr)
    if not location:
        Cachedata[addr] = (None, None)
        return Cachedata[addr]

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
        found = False
        if pt.within(district_polygons[district]):
            constituents[district].append(addrline)
            found = True
            break
    else:
        constituents["unknown"].append(addrline)


def districts_for_addresses(addressfile, district_json):
    district_polygons = load_geojson(district_json)

    with open(addressfile) as fp:
        for addrline in fp:
            handle_address(addrline, district_polygons)

    with open(CACHEFILE, 'w') as fp:
        json.dump(Cachedata, fp, indent=2)
    return constituents


if __name__ == '__main__':
    # Called as a CGI?
    if 'REQUEST_METHOD' in os.environ:
        district_polygons = load_geojson(
            "../../districtmaps/data/NM_Senate.json")
        import cgi
        form = cgi.FieldStorage()
        if 'addresses' in form:
            addresses = unquote_plus(form["addresses"].value)
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

    constituents = districts_for_addresses(sys.argv[1], sys.argv[2])

    print()
    for dist in sorted(constituents.keys(), key=district_sort_key):
        print("\nDistrict", dist)
        if constituents[dist]:
            for addr in constituents[dist]:
                print("   ", addr)
        else:
            print("    No constituents")
