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

from maputils import haversine_distance_bearing, dest_from_bearing
from maputils import read_GNIS_file


def viewshed2view(demfile, lon, lat, start_image=None, peak_gnis=None,
                  outfile="view.png", outwidth=1080, outheight=800):
    '''Turn a GRASS viewshed into a panorama of mountain locations.
       demfile is a file in a format gdal can open, e.g. GeoTIFF.
       lon, lat are in degrees.
       outwidth and outheight are the size of the generated image.
       start_image is an optional image to label, like a povray 3d pano.
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

    # If a starting image was specified, use it as a starting point,
    # and use its size rather than outwidth and outheight
    if start_image:
        im = Image.open(start_image)
        outwidth, outheight = im.size
        heightscale = outheight / 90

    else:
        # Draw it onto a new image
        im = Image.new('RGBA', (outwidth, outheight), (0, 0, 0, 0))
        heightscale = outheight

    print("outheight is", outheight, "heightscale is", heightscale)

    draw = ImageDraw.Draw(im)
    rectsize = 1
    for i, heightlist in enumerate(ridgelist):
        bearing = i * 360. / len(ridgelist)
        for height in heightlist:
            # Height is an angle, where 0 means straight down, 90 horizontal,
            # 180 straight up.
            x = bearing * outwidth / 360
            y = outheight - height * heightscale
            draw.rectangle(((x, y), (x+rectsize, y+rectsize)), fill="yellow")

    # Unbelievably, PIL seems to have no way to draw text without first
    # knowing the absolute pathname of a font's ttf file.
    # There's a call ImageFont.load_default() but that loads a bitmap font
    # at a fixed size so tiny it's unreadable.
    # Don't ask me what encoding="unic" means, it's not documented anywhere.
    font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBoldOblique.ttf",
                              18, encoding="unic")

    for peak in peaks_seen:
        if peak:
            x = peak['bearing'] * outwidth / 360
            # y = outheight - peak['alt'] * outheight / 180
            # XXX Try to tune heightscale to match the undocumented
            # camera angles in a povray image.
            y = outheight/2 - peak['alt'] * heightscale

            # XXX Temporary for testing, until there are labels
            if peak['name'] == 'Black Mesa' or peak['name'] == 'Montoso Peak' \
               or peak['name'] == 'Lake Peak':
                print(peak['name'], "y", y)
                PEAKLINE = 50

                # Get the text size.
                # You can get it roughly like this:
                # w, h = draw.textsize(peak['name'], font=font)
                # but draw.textsize apparently doesn't account for
                # different character widths, which this does better:
                w, h = font.getsize(peak['name'])
                # Everybody says to use 'L' here for the mode, but that
                # doesn't work, need to use 'RGBA'.
                label = Image.new('RGBA', (w, h))
                ImageDraw.Draw(label).text((0, 0), peak['name'],
                                           font=font, fill=(255,255,255,255))
                label = label.rotate(80, expand=1)
                sx, sy = label.size
                # The label size is floating point numbers, which don't
                # work if you pass them to paste().
                im.paste(label, (int(x - sx/3), int(y - PEAKLINE - sy - 3)))

            else:
                PEAKLINE = 20

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

    parser.add_argument('-i', '--image', dest='image',
                        help="Image to start with, e.g. a 360 povray pano")

    parser.add_argument('-p', '--peaknames', dest='peakfile',
                        help="a GNIS CSV file with | separator")

    # Required arguments:
    parser.add_argument('viewshed'
                        , help="Viewshed file; GeoTIF format recommended")
    parser.add_argument('lat', type=float, help="latitude")
    parser.add_argument('lon', type=float, help="longitude")

    args = parser.parse_args(sys.argv[1:])


    if not os.path.exists(args.viewshed):
        print("%s: no such file" % args.viewshed)
        sys.exit(1)
    viewshed2view(args.viewshed, args.lon, args.lat,
                  start_image=args.image, peak_gnis=args.peakfile)


