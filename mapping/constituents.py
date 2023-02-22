#!/usr/bin/env python3


import requests
from collections import defaultdict
from urllib.parse import urlencode, quote_plus
import json
from shapely.geometry import Point, Polygon
from geopy.geocoders import Nominatim


Geolocator = Nominatim(user_agent="constituents")


def geocode(addr):
    """Geocode a single address using GeoPY/Nominatim.
       Returns a (lat, lon) pair, or None, None.
    """
    location = Geolocator.geocode(addr)
    if not location:
        return None, None
    # Nominatim returns a tuple of number, street, city, county,state, zip,
    # (lat, lon)
    return location[-1]


def geocode_census(addr):
    """Geocode a single address using the US Census API.
       Returns a (lat, lon) pair, or None, None.
       But the census API is extremely flaky and often fails,
       so it's not reliable enough to use.
    """
    url = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress'
    url += '?benchmark=Public_AR_Current'
    url += '&vintage=Current'
    url += '&format=json'
    url += '&address=' + quote_plus(addr)

    # print("url:", url)
    # print()

    r = requests.get(url)
    dataj = r.json()

    if not dataj['result']['addressMatches']:
        return None, None

    firstmatch = dataj['result']['addressMatches'][0]

    # Weirdly, they call the coordinates x and y, not longitude/latitude
    return (float(firstmatch['coordinates']['y']),
            float(firstmatch['coordinates']['x']))


# The Census claims to offer batch geocoding, but apparently they
# continually tweak that API, meaning that none of the examples
# on the web or even the curl example in the official documentation
# actually work any more.
# So don't use this.
def addresses_to_districts(addressfile):
    """Input: a filename containing addresses in text format, one per line.
       Output: a list of dictionaries of { "id": int, "addr": str,
                                           "lat": float, "lon": float }
    """
    output = {}
    url = 'https://geocoding.geo.census.gov/geocoder/locations/addressbatch'
    # Get a list of vintages with:
    # https://geocoding.geo.census.gov/geocoder/vintages?benchmark=Public_AR_Current
    payload = { 'benchmark':'Public_AR_Current',
                # 'vintage':'ACS2013_Current'
               }
    # files = { 'addressFile': open(addressfile, 'rb') }
    if addressfile.endswith(".csv"):
        mimetype = "text/csv"
    else:
        mimetype = "text/plain"
    files = { 'addressFile': (addressfile, open(addressfile, 'rb'), mimetype)
            }
    r = requests.get(url, files=files, data=payload)


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

    for dist in sorted(constituents.keys(), key=district_sort_key):
        print("\nDistrict", dist)
        if constituents[dist]:
            for addr in constituents[dist]:
                print("   ", addr)
        else:
            print("    No constituents")


if __name__ == '__main__':
    import sys

    districts_for_addresses(sys.argv[1], sys.argv[2])
