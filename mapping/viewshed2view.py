#!/usr/bin/env python

# Given a viewshed file, generate a 360-degree panorama showing
# outlines of peaks/ridges visible from a given latitude/longitude.
# Optionally, label peaks with names from a GNIS file.

# The viewshed file should be in an image format with
# geographic references, and must include visibility angles
# (e.g. GRASS r.viewshed's default output setting).
# GeoTIF is the recommended input format and the only format I've tested.

# See grassviewshed.py for generating viewsheds using GRASS.

# Copyright 2019 by Akkana Peck; share and enjoy under the GPLv2 or later.

from __future__ import print_function

import gdal
import numpy as np
import affine

from PIL import Image, ImageDraw, ImageFont

import csv

import argparse
import sys, os
import math


earthR = 6378.1    # Earth radius in km


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


def viewshed2view(demfile, lon, lat, peak_gnis=None,
                  outfile="view.png", outwidth=800, outheight=600):
    '''Turn a GRASS viewshed into a panorama of mountain locations.
       demfile is a file in a format gdal can open, e.g. GeoTIFF.
       lon, lat are in degrees.
       outwidth and outheight are the size of the generated image.
       peaknames is an optional GPX waypoint file containing locations
       and names of mountain peaks.
    '''
    demdata = gdal.Open(demfile)
    demarray = np.array(demdata.GetRasterBand(1).ReadAsArray())
    affine_transform = affine.Affine.from_gdal(*demdata.GetGeoTransform())
    inverse_transform = ~affine_transform
    obs_x, obs_y = [ round(f) for f in inverse_transform * (lon, lat) ]
    imheight, imwidth = demarray.shape
    # In Python 2, numpy array indices can't be float:
    obs_ele = demarray[int(obs_x), int(obs_y)]
    lon_rad = math.radians(lon)
    lat_rat = math.radians(lat)
    # print("Observer is at pixel position", obs_x, obs_y)
    # print("Image size %d x %d" % (imwidth, imheight))

    # Read in the peak list, if any.
    if peak_gnis:
        peaklist = read_GNIS_file(peak_gnis)

        # For each peak in the peak list, figure out its bearing and distance
        # from our observer, and where it would be in pixel coordinates
        # on the image.
        for peak in peaklist:
            d, bearing = haversine_distance_bearing(lon, lat,
                                                    peak['lon'], peak['lat'])
            peak['dist'] = d
            peak['bearing'] = round(bearing)

            peak['x'], peak['y'] = [ round(f)
                for f in inverse_transform * (peak['lon'], peak['lat']) ]
    else:
        peaklist = []

    # Distance resolution in meters
    step_m = 100.0

    # For higher vertical resolution, you might want to use a higher
    # angular resolution than 1 degree. But 1 seems enough for the vertical
    # resolution in typical GRASS r.viewshed geotiff files.
    binmult = 1
    nbins = 360 * binmult

    # Save ridges as a list with nbins elements,
    # each of which is a list of view angles where peaks were seen.
    # Can't do [[]] * 360 -- that makes 360 pointers to the same list!
    ridgelist = [ [] for i in range(nbins) ]

    peaks_seen = [ None for i in range(nbins) ]

    # How close does a peak have to be (max pixel distance in any direction)
    # to match a named peak?
    PEAKSLOP = 4

    # Loop over a full circle:
    for bearing_i in range(nbins):
        bearing = float(bearing_i) / binmult
        bearingrad = math.radians(bearing)
        dist_m = step_m
        lastval = 0

        # Loop over distances at this bearing, from close to far
        while True:
            # Find the coordinate for point with this bearing and distance
            destlon, destlat = dest_from_bearing(lon, lat,
                                                 bearingrad, dist_m / 1000)
            # and translate that back to pixels
            px, py = [ round(f)
                       for f in inverse_transform * (destlon, destlat) ]

            # value of the viewshed image, which is the vertical
            # angle in degrees (0 being straight down, 90 horizontal)
            # to whatever is at that point.
            try:
                val = demarray[int(py), int(px)]
            except IndexError:
                # Outside the image, done with this bearing
                break

            if math.isnan(val) and lastval and not math.isnan(lastval):
                # lastval was a peak, and now we're past it heading downhill.
                # Record the peak.
                ridgelist[bearing_i].append(lastval)

                # does it correspond to a peak in the peaklist?
                for peak in peaklist:
                    if round(bearing) == peak['bearing'] and \
                       abs(peak['x'] - px) < PEAKSLOP and \
                       abs(peak['y'] - py) < PEAKSLOP:
                        peak['alt'] = lastval
                        peaks_seen[bearing_i] = peak

            lastval = val

            dist_m += step_m

    # Draw it onto a new image
    outwidth = 1080
    outheight = 800
    im = Image.new('RGBA', (outwidth, outheight), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    rectsize = 1
    for i, heightlist in enumerate(ridgelist):
        bearing = i * 360. / len(ridgelist)
        for height in heightlist:
            # Height is an angle, where 0 means straight down, 90 horizontal,
            # 180 straight up.
            x = bearing * outwidth / 360
            y = outheight - height * outheight / 180
            draw.rectangle(((x, y), (x+rectsize, y+rectsize)), fill="yellow")

    # Unbelievably, PIL seems to have no way to draw text without first
    # knowing the absolute pathname of a font's ttf file.
    # There's a call ImageFont.load_default() but that loads a bitmap font
    # at a fixed size so tiny it's unreadable.
    font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBoldOblique.ttf",
                              20, encoding="unic")

    for peak in peaks_seen:
        if peak:
            x = peak['bearing'] * outwidth / 360
            y = outheight - peak['alt'] * outheight / 180

            # XXX Temporary for testing, until there are labels
            if peak['name'] == 'Black Mesa' or peak['name'] == 'Montoso Peak' \
               or peak['name'] == 'Lake Peak':
                PEAKLINE = 50

                # Get the text size.
                # You can get it roughly like this:
                # w, h = draw.textsize(peak['name'], font=font)
                # but draw.textsize apparently doesn't account for
                # different character widths, which this does better:
                w, h = font.getsize(peak['name'])

                draw.text((x - w/2, y - PEAKLINE - h), peak['name'],
                          font=font, fill=(255,255,255,255))

            else:
                PEAKLINE = 20

            # print("(%4d, %4d) %s" % (x, y, peak['name']))

            draw.line(((x, y), (x, y-PEAKLINE)), fill="white")

    # im.show()
    im.save(outfile)
    print("Saved to", outfile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=""
        """Convert a viewshed file to a 360-degree view from a given point.

Coordinates are specified in decimal degrees""",
                                     formatter_class=
                                         argparse.RawTextHelpFormatter)

    parser.add_argument('-p', '--peaknames', dest='peakfile',
                        help="a GNIS CSV file with | separator")

    # Required arguments:
    parser.add_argument('viewshed'
                        , help="Viewshed file; GeoTIF format recommended")
    parser.add_argument('lat', type=float, help="latitude")
    parser.add_argument('lon', type=float, help="longitude")

    args = parser.parse_args(sys.argv[1:])

    viewshed2view(args.viewshed, args.lon, args.lat, peak_gnis=args.peakfile)


