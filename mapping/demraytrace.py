#!/usr/bin/env python3

# Generate a 360-degree panorama of raytraced terrain views
# from a Digital Elevation Model (DEM) file and observer coordinates,
# using povray. Input DEM must be in a format povray understands,
# like PNG, as discussed in
# http://shallowsky.com/blog/mapping/DEM-data-in-3d.html

# Copyright 2019 by Akkana Peck; share and enjoy under the GPLv2 or later.

from __future__ import print_function

import gdal
import numpy as np
import affine

from PIL import Image, ImageDraw, ImageFont

import sys, os
import subprocess
import math

from maputils import haversine_distance, haversine_distance_bearing, \
     read_GNIS_file


def raytrace_DEM_file(demfile, lon, lat,
                      outwidth=3600, outheight=1800,
                      outfilename="povray360.png"):
    '''Use povray to raytrace an input Digital Elevation Model.
       demfile is a file in a format gdal can open, e.g. GeoTIFF.
       lon, lat are in degrees.
       outwidth and outheight are the size of the generated image.
    '''
    demdata = gdal.Open(demfile)
    demarray = np.array(demdata.GetRasterBand(1).ReadAsArray())
    affine_transform = affine.Affine.from_gdal(*demdata.GetGeoTransform())
    inverse_transform = ~affine_transform
    obs_x, obs_y = [ round(f) for f in inverse_transform * (lon, lat) ]
    imheight, imwidth = demarray.shape
    # In Python2, numpy can't deal with floating point indices:
    obs_ele = demarray[int(obs_x), int(obs_y)]
    lon_rad = math.radians(lon)
    lat_rat = math.radians(lat)

    # povray doesn't work if you view from ground level.
    # I don't know what the rules are or if it's better to multiply
    # or add a fudge factor.
    # multiplying by 1.15 seems to work (1.1 doesn't).
    heightfudge = 1.15

    # How big a circle, in km, can we draw around the observer
    # while staying inside the image?
    # Note that affine_transform returns degrees, not radians,
    # so that's what we need to pass to haversine_distance.

    # Edge of image north of observer:
    northlon, northlat = affine_transform * (obs_x, 0)
    northdist = haversine_distance(lon, lat, northlon, northlat)
    # Edge of image south of observer:
    southlon, southlat = affine_transform * (obs_x, imheight)
    southdist = haversine_distance(lon, lat, southlon, southlat)
    # Edge of image west of observer:
    westlon, westlat = affine_transform * (0, obs_y)
    westdist = haversine_distance(lon, lat, westlon, westlat)
    # Edge of image east of observer:
    eastlon, eastlat = affine_transform * (imwidth, obs_y)
    eastdist = haversine_distance(lon, lat, eastlon, eastlat)

    # Minimum of the distances to image edge in the four cardinal directions:
    obsradius = min(northdist, southdist, westdist, eastdist)

    print("Image size is %dx%d" % (imwidth, imheight))
    print("Observer is at (%d, %d)" % (obs_x, obs_y))
    print("Distance (km): north", northdist, "south", southdist,
          "west", westdist, "east", eastdist)
    print("Min dist:", obsradius)

    if obsradius < 3:
        print("Observer is too close to the edge")
        return

    povfilename = '/tmp/povfile.pov'

    povfiletext = '''
camera {
    // "perspective" is the default camera, which warps images
    // so they're hard to stitch together.
    // panoramic sounds tempting but also warps.
    // "cylinder 1" uses a vertical cylinder.
    cylinder 1

    // povray coordinates compared to the height field image are
    // < rightward, upward, forward >
    location <%f, %f, %f>
    look_at  <%f, %f, 0>

    angle 360
}

light_source { <2, 1, -1> color <1,1,1> }

height_field {
    png "%s"
    smooth
    pigment {
        gradient y
        color_map {
            [ 0 color <.8 .8 .8> ]
            [ 1 color <1 1 1> ]
        }
    }

    scale <1, 1, 1>
}
''' % (obs_x / imwidth, heightfudge * obs_ele / 65536, 1. - obs_y / imheight,
       obs_x / imwidth, heightfudge * obs_ele / 65536,
       demfile)

    with open(povfilename, 'w') as pf:
        pf.write(povfiletext)

    print("Generating 360", outfilename)
    subprocess.call(['povray', '+A', '+W%d' % outwidth, '+H%d' % outheight,
                     '+I' + povfilename, '+O' + outfilename])

    print("Wrote", outfilename)
    return outfilename


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: %s demfile.png lat lon" % os.path.basename(sys.argv[0]))
        print("DEM file must be PNG. Lat, lon in decimal degrees.")
        sys.exit(1)

    demfile = sys.argv[1]
    lat = float(sys.argv[2])
    lon = float(sys.argv[3])
    print("Observer is at latitude %f, longitude %f" % (lat, lon))

    outfilename = raytrace_DEM_file(demfile, lon, lat,
                                    outwidth=2000, outheight=1000)

