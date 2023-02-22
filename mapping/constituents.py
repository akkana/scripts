#!/usr/bin/env python3


import requests
from collections import defaultdict
from urllib.parse import urlencode, quote_plus
import json
from shapely.geometry import Point, Polygon
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import sys


Geolocator = Nominatim(user_agent="constituents")

# Nominatim has a limit of 1 request per second for free non-OSM use.
# (They don't always enforce this, but be nice and follow the guidelines!)
Geocode = RateLimiter(Geolocator.geocode, min_delay_seconds=1)
print("Geolocation courtesy of OpenStreetMap/Nominatim")
print("Warning: rate limiting to 1 address per second.")
print("For faster bulk queries, consider using OpenMapQuest or PickPoint")
print("(see https://geopy.readthedocs.io/en/latest/#geopy-is-not-a-service)")


def geocode(addr):
    """Geocode a single address using GeoPY/Nominatim.
       Returns a (lat, lon) pair, or None, None.
    """
    location = Geocode(addr)
    if not location:
        return None, None
    # Nominatim returns a tuple of number, street, city, county,state, zip,
    # (lat, lon)
    return location[-1]


def load_geojson(geojson_file):
    with open(geojson_file, 'rb') as fp:
        district_json = json.load(fp)
        district_polygons = {}
        for feature in district_json['features']:
            district_polygons[feature["properties"]["DIST"]] = \
                Polygon(feature['geometry']['coordinates'][0])

        # Done with json
        district_json = None
    print("Found", len(district_polygons), "districts in", geojson_file)
    return district_polygons


def district_sort_key(k):
    if type(k) is int:
        return "%03d" % k
    return "%03s" % k


def districts_for_addresses(addressfile, district_json):
    district_polygons = load_geojson(district_json)

    constituents = defaultdict(list)
    with open(addressfile) as fp:
        for addrline in fp:
            addrline = addrline.strip()
            print(".", end="")
            sys.stdout.flush()
            try:
                lat, lon = geocode(addrline)
            except:
                lat = None
                lon = None
            if not lat or not lon:
                # print("Couldn't geocode", addrline)
                constituents["address error"].append(addrline)
                continue

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

    return constituents


if __name__ == '__main__':
    constituents = districts_for_addresses(sys.argv[1], sys.argv[2])

    print()
    for dist in sorted(constituents.keys(), key=district_sort_key):
        print("\nDistrict", dist)
        if constituents[dist]:
            for addr in constituents[dist]:
                print("   ", addr)
        else:
            print("    No constituents")
