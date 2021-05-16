#!/usr/bin/env python3

# Given two rectangular Earth images, day and night,
# generate a combined image for a given time.

import ephem
import math
from datetime import datetime, timezone
from PIL import Image
import os, sys


# How many degrees wide should the blur zone be? BLUR is half the blur width.
BLURANGLE = 3

def subsolar_point(obstime):
    """Return lon, lat of the earth's subsolar point at the given UTC datetime.
    """
    gmt_obs = ephem.Observer()
    gmt_obs.lat = "0"
    gmt_obs.lon = "0"
    gmt_obs.date = obstime
    sun = ephem.Sun(gmt_obs)
    sun.compute(gmt_obs.date)
    sun_lon = math.degrees(sun.ra - gmt_obs.sidereal_time())
    if sun_lon < -180.0 :
        sun_lon = 360.0 + sun_lon
    elif sun_lon > 180.0 :
        sun_lon = sun_lon - 360.0
    sun_lat = math.degrees(sun.dec)
    return sun_lon, sun_lat


def haversine_angle(longitude_1, latitude_1, longitude_2, latitude_2):
    """Haversine distance between two points.
       From https://github.com/tkrajina/gpxpy/blob/master/gpxpy/geo.py
       Implemented from http://www.movable-type.co.uk/scripts/latlong.html
       We don't really want the distance, rather the interior angle.
       Return angle in degrees.
    """
    d_lat = math.radians(latitude_1 - latitude_2)
    d_lon = math.radians(longitude_1 - longitude_2)
    lat1 = math.radians(latitude_1)
    lat2 = math.radians(latitude_2)

    a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
        math.sin(d_lon / 2) * math.sin(d_lon / 2) * \
        math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return math.degrees(c)


def combine_images(day_imgfile, night_imgfile, sublon, sublat, out_imgfile):
    """Given filenames for a day and a night image,
       and a subsolar longitude and latitude,
       combine the two images and write the result to a new image file.
       But if the image exists already, skip it, don't overwrite.
    """
    if os.path.exists(out_imgfile):
        return
    print("Opening", day_imgfile)
    dayimg = Image.open(day_imgfile)
    print("Opening", night_imgfile)
    nightimg = Image.open(night_imgfile)
    # *img.shape is height, width, depth
    w, h = dayimg.size
    halfwidth = w/2
    halfheight = h/2

    lon_conversion = 180. / halfwidth
    lat_conversion = 90. / halfheight

    # Iterate over pixels
    dayimg_px = dayimg.load()
    nightimg_px = nightimg.load()
    for y in range(h):
        lat = (halfheight - y) * lat_conversion
        for x in range(w):
            # pxl is the RGB 3-element array at (x, y)
            lon = (x - halfwidth) * lon_conversion

            # The Haversine angle will be between 0 and 180 degrees.
            havangle = haversine_angle(sublon, sublat, lon, lat)
            if havangle > 90 + BLURANGLE:
                # full night
                dayimg_px[x, y] = nightimg_px[x, y]
            elif havangle > 90 - BLURANGLE and havangle < 90 + BLURANGLE:
                # twilight, blur zone.
                blur = (90 + BLURANGLE - havangle) / BLURANGLE / 2.
                # Each pixel is a tuple, so make a new tuple:
                newpx = []
                for i, c in enumerate(dayimg_px[x, y]):
                    newpx.append(int(dayimg_px[x, y][i] * blur
                                     + nightimg_px[x, y][i] * (1. - blur)))
                dayimg_px[x, y] = tuple(newpx)

            # else it's daylight, don't do annything

    # dayimg.show()
    dayimg.save(out_imgfile)


def calc_for_date(obstime, out_imgfile):
    sublon, sublat = subsolar_point(obstime)
    print(sublon, sublat)
    combine_images(dayimgfile, nightimgfile, sublon, sublat, out_imgfile)
    print("Wrote to", out_imgfile)


if __name__ == '__main__':
    dayimgfile = "maps/color_etopo1_ice-1600.jpg"
    nightimgfile = "maps/BlackMarble-1600.jpg"

    print("\nSummer solstice rise...")
    calc_for_date(datetime(2021, 6, 20, 12, 0, tzinfo=timezone.utc),
                  "maps/ss-sunrise.jpg")
    print("\nSummer solstice sunset...")
    calc_for_date(datetime(2021, 6, 21, 3, 0, tzinfo=timezone.utc),
                  "maps/ss-sunset.jpg")
    print("\nWinter solstice ...")
    calc_for_date(datetime(2021, 12, 21, 0, 0, tzinfo=timezone.utc),
                  "maps/ws-sunset.jpg")


