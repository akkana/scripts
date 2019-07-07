#!/usr/bin/env python3

import sys, os
import subprocess

import gdal
import numpy as np
import affine


def handle_DEM_file(demfile, lat, lon):
    demdata = gdal.Open(demfile)
    demarray = np.array(demdata.GetRasterBand(1).ReadAsArray())
    affine_transform = affine.Affine.from_gdal(*demdata.GetGeoTransform())
    inverse_transform = ~affine_transform
    obs_x, obs_y = [ round(f) for f in inverse_transform * (lon, lat) ]
    print("Observer is at pixel position", obs_x, obs_y)
    imheight, imwidth = demarray.shape
    obs_ele = demarray[obs_x, obs_y]
    outwidth = 800
    outheight = 600

    # povray doesn't work if you view from ground level.
    # I don't know what the rules are or if it's better to multiply
    # or add a fudge factor.
    # multiplying by 1.15 seems to work (1.1 doesn't).
    heightfudge = 1.15

    # Quick fudge at the eight cardinal points;
    # in reality this should calculate bearing angles from the observer.
    lookats = { 'N': (.5, 1), 'NE': (1, 1), 'E': (1, .5), 'SE': (1, 0),
                'S': (.5, 0), 'SW': (0, 0), 'W': (0, .5), 'NW': (0, 1) }

    for l in lookats:
        outfilename = 'outfile%s.png' % l
        povfilename = '/tmp/povfile.pov'

        povfiletext = '''
camera {
    // "perspective" is the default camera.
    // It will probably make it hard to stitch multiple images together.

    // "orthographic" projection might make it easiest to stitch
    // multiple images together; it requires also specifying "angle"
    // to get reasonable scaling.
    orthographic
    angle

    // "cylinder 1" is a vertical cylinder and doesn't need angle.
    // cylinder 1

    // povray coordinates are < rightward, upward, forward >

    location <%f, %f, %f>
    look_at  <%f, %f, %f>
}

light_source { <2, 1, -1> color <1,1,1> }

height_field {
    png "%s"
    smooth
    pigment {
        gradient y
        color_map {
            // Adjusting the 0 color can make darks a little brighter,
            // otherwise everything comes out super dark.
            // [ 0 color <.25 .25 .25> ]
            [ 0 color <.7 .7 .7> ]
            [ 1 color <1 1 1> ]
        }
    }

    scale <1, 1, 1>
}
''' % (obs_x / imwidth, heightfudge * obs_ele / 65536, 1. - obs_y / imheight,
       lookats[l][0], heightfudge * obs_ele / 65536, lookats[l][1],
       demfile)

        with open(povfilename, 'w') as pf:
            pf.write(povfiletext)

        print("Generating", outfilename)
        subprocess.call(['povray', '+A', '+W%d' % outwidth, '+H%d' % outheight,
                         '+I' + povfilename, '+O' + outfilename])


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: %s demfile.png lat lon" % os.path.basename(sys.argv[0]))
        print("DEM file must be PNG. Lat, lon in decimal degrees.")
        sys.exit(1)

    demfile = sys.argv[1]
    lat = float(sys.argv[2])
    lon = float(sys.argv[3])

    handle_DEM_file(demfile, lat, lon)

