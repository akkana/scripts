#!/usr/bin/env python3

# Given two rectangular Earth images, day and night,
# generate a combined image for a given time.

import ephem
from ephem import cities
import math
from datetime import datetime, timezone, timedelta
from PIL import Image
import os, sys


# How many degrees wide should the blur zone be? BLUR is half the blur width.
BLURANGLE = 3

sun = ephem.Sun()


def subsolar_point(obstime):
    """Return lon, lat of the earth's subsolar point at the given UTC datetime.
    """
    gmt_obs = ephem.Observer()
    gmt_obs.lat = "0"
    gmt_obs.lon = "0"
    gmt_obs.date = obstime
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
    dayimg = Image.open(day_imgfile)
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
    print("calc", obstime.datetime())
    sublon, sublat = subsolar_point(obstime)
    print("Subsolar point:", sublon, sublat)
    combine_images(dayimgfile, nightimgfile, sublon, sublat, out_imgfile)
    print("Wrote to", out_imgfile)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] == "-h" or sys.argv[1] == "--help":
            Usage()
        observer = cities.lookup(city)

    elif len(sys.argv) == 3:
        observer = ephem.Observer()
        observer.lat = sys.argv[1]
        observer.lon = sys.argv[2]
        observer.elevation = 100
        observer.name = "Observer at %s, %s" % (observer.lon, observer.lat)

    else:
        # Default to Los Alamos Nature Center
        observer = ephem.Observer()
        observer.lat = '35:53.1'     # 35.8849756
        observer.lon = '-106:18.36'  # -106.3061510
        observer.elevation = 2100
        observer.name = "Observer at %s, %s" % (observer.lon, observer.lat)

    print(observer)

    # Set date to the next solstice or equinox, whichever comes first.
    # This is just because of being lazy about setting up arguments
    # to specify which event the user is looking for.
    next_solstice = ephem.next_solstice(observer.date)
    print("Next solstice:", next_solstice.datetime())
    next_equinox = ephem.next_equinox(observer.date)
    print("Next equinox:", next_equinox.datetime())
    if next_solstice < next_equinox:
        event_time = next_solstice.datetime()
        if event_time.month == 6:
            event = "Summer Solstice"
            mapname = "ss"
        else:
            event = "Winter Solstice"
            mapname = "ws"
    else:
        event_time = next_equinox.datetime()
        if event_time.month == 3:
            event = "Vernal Equinox"
            mapname = "ve"
        else:
            event = "Autumnal Equinox"
            mapname = "ae"

    print("Event:", event)

    observer.date = event_time
    risetime = observer.next_rising(sun)
    dt = risetime.datetime()
    # ephem Date.datetime() produces an unaware datetime
    # where the time is actually URC, but there's no timezone attached.
    # If you take that unaware datetime and do .astimezone(timezone.utc),
    # datetime assumes the unaware time was in the local timezone
    # and so converts it.
    # Instead, you have to do astimezone() to make it aware
    # in the local timezone, then replace the timezone with UTC.
    dt = dt.astimezone().replace(tzinfo=timezone.utc)
    print("rise time now:", dt)

    observer.date = risetime
    settime = observer.next_setting(sun)
    print("unaware settime", settime.datetime())
    set_dt = settime.datetime().astimezone().replace(tzinfo=timezone.utc)
    print("utc", set_dt)

    dayimgfile = "maps/color_etopo1_ice-1600.jpg"
    nightimgfile = "maps/BlackMarble-1600.jpg"

    print("\n%s sunrise" % event)
    calc_for_date(risetime, "maps/%s-sunrise.jpg" % mapname)

    print("\nLooping from", dt, "to", set_dt)
    interval = timedelta(hours=1)
    while True:
        dt += interval
        if dt > set_dt:
            break
        localdt = dt.astimezone()
        print("utc", dt, "local", localdt)
        observer.date = dt
        calc_for_date(ephem.Date(dt),
                      "maps/%s-%s.jpg" % (mapname, localdt.strftime("%H")))

    print("\n%s sunset" % event)
    calc_for_date(settime, "maps/%s-sunset.jpg" % mapname)


