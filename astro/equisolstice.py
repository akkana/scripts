#!/usr/bin/env python3

# Very simple PyEphem script to show the next four solstices/equinoxes.

import ephem
import ephem.cities
from datetime import datetime, timezone


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


observer = ephem.Observer()
observer.lat = '35:53.1'     # 35.8849756
observer.lon = '-106:18.36'  # -106.3061510
observer.elevation = 2100    # About 7000'
observer.name = "Los Alamos Nature Center"

# La Senda, to match my XEphem settings
observer.lat = '35:40.50'
observer.lon = '-106:13.10'
observer.elevation = 1980

FMT = "%17s   %-20s %-20s"
TIMEFMT = "%Y-%m-%d  %H:%M"


def print_stats(name, ephemtime):
    def local_and_ut(ephemdate):
        """Convert an ephem.Date to datetime.datetime.
           Return aware (localdatetime, utcdatetime)
        """
        dt = ephemdate.datetime()
        dt = dt.astimezone().replace(tzinfo=timezone.utc)
        return (dt.astimezone(), dt)

    print()
    print(FMT % ("", "Local", "UTC"))

    lt, ut = local_and_ut(ephemtime)
    if lt.month == 3:
        season = "Vernal"
    elif lt.month == 6:
        season = "Summer"
    elif lt.month == 9:
        season = "Autumnal"
    elif lt.month == 12:
        season = "Winter"
    else:
        season = ""

    name = "%s %s" % (season, name)

    print(FMT % (name, lt.strftime(TIMEFMT), ut.strftime(TIMEFMT)))

    halfdaybefore = ephem.Date(ephemtime - .5)
    observer.date = halfdaybefore
    sunrise = observer.next_rising(sun)
    observer.date = sunrise
    lt_sunrise, ut_sunrise = local_and_ut(observer.date)

    sunset = observer.next_setting(sun)
    observer.date = sunset
    lt_sunset, ut_sunset = local_and_ut(observer.date)

    cities = find_similar_cities(halfdaybefore, sunrise, sunset)

    print("------------------------------------------------")
    print(FMT % ("** SUNRISE",
                 lt_sunrise.strftime(TIMEFMT),
                 ut_sunrise.strftime(TIMEFMT)))
    cities.sort(key=lambda c: c[1])
    for c in cities[:5]:
        lt, ut = local_and_ut(c[3])
        print(FMT % (c[0], lt.strftime(TIMEFMT), ut.strftime(TIMEFMT)))

    print("------------------------------------------------")
    print(FMT % ("** SUNSET",
                 lt_sunset.strftime(TIMEFMT),
                 ut_sunset.strftime(TIMEFMT)))
    cities.sort(key=lambda c: c[2])
    for c in cities[:5]:
        lt, ut = local_and_ut(c[4])
        print(FMT % (c[0], lt.strftime(TIMEFMT), ut.strftime(TIMEFMT)))


def find_similar_cities(halfdaybefore, sunrise, sunset):
    """Search through pyephem's list of cities and return a list
       of each city and the difference between its sunrise/sunset times
       and the times passed in. So return a list of:
       [cityname, abs_difference_sunrise, abs_difference_sunset,
        sunrise, sunset]
       where the last two are ephem.Dates.
       You can sort the list on the abs difference columns
       to find the most similar cities.
    """
    cities = []
    for city in ephem.cities._city_data:
        city_obs = ephem.city(city)
        city_obs.date = halfdaybefore
        city_sunrise = city_obs.next_rising(sun)
        city_obs.date = sunrise
        city_sunset = city_obs.next_setting(sun)
        cities.append([city,
                       abs(city_sunrise - sunrise),
                       abs(city_sunset - sunset),
                       city_sunrise, city_sunset])

    return cities



next_solstice = ephem.next_solstice(observer.date)
print_stats("Solstice", next_solstice)

next_equinox = ephem.next_equinox(next_solstice)
print_stats("Equinox", next_equinox)

second_solstice = ephem.next_solstice(next_equinox)
print_stats("Solstice", second_solstice)

second_equinox = ephem.next_equinox(second_solstice)
print_stats("Equinox", second_equinox)



