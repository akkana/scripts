#!/usr/bin/env python3


import gdal
import numpy as np
import affine

from PIL import Image, ImageDraw

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


def viewshed2view(demfile, lon, lat, peak_gpx=None,
                  outwidth=800, outheight=600):
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
    obs_ele = demarray[obs_x, obs_y]
    lon_rad = math.radians(lon)
    lat_rat = math.radians(lat)
    # print("Observer is at pixel position", obs_x, obs_y)
    # print("Image size %d x %d" % (imwidth, imheight))

    # Distance resolution in meters
    step_m = 100

    # For higher vertical resolution, you might want to use a higher
    # angular resolution than 1 degree. But 1 is plenty for the vertical
    # resolution in typical GRASS r.viewshed geotiff files.
    binmult = 1
    nbins = 360 * binmult

    # Save peaks as a list with nbins elements,
    # each of which is a list of view angles where peaks were seen.
    # Can't do [[]] * 360 -- that makes 360 pointers to the same list!
    savepeaks = [ [] for i in range(nbins) ]

    for bearing_i in range(nbins):
        bearing = bearing_i / binmult
        bearingrad = math.radians(bearing)
        dist_m = step_m
        lastval = 0
        while True:
            # Find the coordinate for point with that bearing and distance
            destlon, destlat = dest_from_bearing(lon, lat,
                                                 bearingrad, dist_m / 1000)
            # and translate that back to pixels
            px, py = [ round(f)
                       for f in inverse_transform * (destlon, destlat) ]

            # value of the viewshed image, corresponding to the vertical
            # angle in degrees (0 being straight down, 90 horizontal)
            # to that point.
            # print(px, py)
            try:
                val = demarray[py][px]
            except IndexError:
                # Outside the image, done with this bearing
                break

            # print("dist %5.1f (%4d, %4d): val %f" % (dist_m/1000, px, py, val))
            if math.isnan(val) and lastval and not math.isnan(lastval):
                # lastval was a peak, and now we're past it heading downhill.
                # Record the peak.
                savepeaks[bearing_i].append(lastval)
                # print(bearing, "Appending", lastval, "now", savepeaks[bearing])

            lastval = val
            # lastcoords = destlon, destlat

            dist_m += step_m

    # Draw it onto a new image
    outwidth = 1080
    outheight = 800
    im = Image.new('RGB', (outwidth, outheight), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    rectsize = 1
    for i, heightlist in enumerate(savepeaks):
        bearing = i * 360. / len(savepeaks)
        for height in heightlist:
            # Height is an angle, where 0 means straight down, 90 horizontal,
            # 180 straight up.
            x = bearing * outwidth / 360
            y = outheight - height * outheight / 180
            draw.rectangle(((x, y), (x+rectsize, y+rectsize)),
                     fill="yellow")
    # im.show()
    im.save('view.png')
    print("Saved to view.png")


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: %s demfile lat lon [peaknames]"
              % os.path.basename(sys.argv[0]))
        print("DEM file must be PNG. Lat, lon in decimal degrees.")
        sys.exit(1)

    demfile = sys.argv[1]
    lat = float(sys.argv[2])
    lon = float(sys.argv[3])

    if len(sys.argv) > 4:
        peak_gpx = sys.argv[4]
    else:
        peak_gpx = None

    viewshed2view(demfile, lon, lat, peak_gpx=peak_gpx)


