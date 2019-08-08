#!/usr/bin/env python3

import math
import csv


earthR = 6378.1    # Earth radius in km


def haversine_distance_bearing(lon1, lat1, lon2, lat2):
    '''
    Haversine distance and bearing between two points.
    Input coordinates are in decimal degrees.
    From https://github.com/tkrajina/gpxpy/blob/master/gpxpy/geo.py
    Implemented from http://www.movable-type.co.uk/scripts/latlong.html
    Returns dist_km, bearing_dd
    '''
    d_lat = math.radians(lat1 - lat2)
    d_lon = math.radians(lon1 - lon2)
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
        math.sin(d_lon / 2) * math.sin(d_lon / 2) * \
        math.cos(lat1) * math.cos(lat2)

    bearing = math.atan2(math.sin(lon2-lon1)*math.cos(lat2),
                         math.cos(lat1) * math.sin(lat2)
                         - math.sin(lat1) * math.cos(lat2)
                           * math.cos(lon2-lon1))
    bearing = math.degrees(bearing)

    return (earthR * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)),
            (bearing + 360) % 360)


def haversine_distance(lon1, lat1, lon2, lat2):
    '''
    Haversine distance between two points.
    Input coordinates are in decimal degrees.
    Returns dist_km
    '''
    return haversine_distance_bearing(lon1, lat1, lon2, lat2)[0]


def dest_from_bearing(srclon, srclat, bearing_rad, dist_km):
    '''Given a source lon and lat in degrees, a bearing in radians,
       and a distance in km, return destination lon, lat in degrees.
    '''
    srclon_rad = math.radians(srclon)
    srclat_rad = math.radians(srclat)
    distfrac = dist_km / earthR

    dstlat_rad = math.asin( math.sin(srclat_rad) * math.cos(distfrac)
                        + (math.cos(srclat_rad) * math.sin(distfrac)
                           * math.cos(bearing_rad)))

    dstlon_rad = srclon_rad \
        +  math.atan2(math.sin(bearing_rad) * math.sin(distfrac)
                      * math.cos(srclat_rad),
                      math.cos(distfrac) - math.sin(srclat_rad)
                      * math.sin(dstlat_rad))

    return math.degrees(dstlon_rad), math.degrees(dstlat_rad)


def read_GNIS_file(filename, verbose=False):
    '''Read a GNIS file, CSV format with | as separator,
       matching the format downloadable from
       https://www.usgs.gov/core-science-systems/ngp/board-on-geographic-names/download-gnis-data
       Return a list of peaks, each a dictionary with keys
       'ele', 'name', 'lat', 'lon', 'county'
    '''
    with open(filename) as csvfp:
        reader = csv.DictReader(csvfp, delimiter='|')
        nodata = []
        peaklist = []

        for row in reader:
            if row['FEATURE_CLASS'] != 'Summit':
                continue
            try:
                elev = int(row['ELEV_IN_FT'])
            except ValueError:
                nodata.append((row['FEATURE_NAME'], row['COUNTY_NAME']))
                continue
            try:
                lat = float(row['PRIM_LAT_DEC'])
            except ValueError:
                nodata.append((row['FEATURE_NAME'], row['COUNTY_NAME']))
                continue
            try:
                lon = float(row['PRIM_LONG_DEC'])
            except ValueError:
                nodata.append((row['FEATURE_NAME'], row['COUNTY_NAME']))
                continue

            if not lat or not lon or not elev:
                nodata.append((row['FEATURE_NAME'], row['COUNTY_NAME']))
                continue

            # If we get this far, there's real data
            # for elevation and coordinates
            peaklist.append({ 'name': row['FEATURE_NAME'],
                              'ele': elev,
                              'lat':  lat, 'lon': lon,
                              'county': row['COUNTY_NAME'] })

        peaklist.sort(reverse=True, key=lambda pk: -pk['ele'])
        # for peak in peaklist:
        #     print("%5d %25s   (%.4f %.4f)  %s" % (peak['ele']))
        # print("Total of", len(peaklist), "peaks with data")

        if verbose:
            nodata.sort()
            print("\nPeaks lacking elevation or coordinates:")
            for peak in nodata:
                print("%s (%s)" % (peak[0], peak[1]))
            print("Total of", len(nodata), "peaks with no data")

        return peaklist


