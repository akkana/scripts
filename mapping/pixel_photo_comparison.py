#!/usr/bin/env python3

"""The Pixel 6a embeds the wrong GPS coordinates in its photos.
   This is a script to plot points from photos to see how far
   off they are, and if they're in a consistent direction (they aren't).
   It's also helpful as an example of how to use folium.BeautifIcon,
   though I have yet to find any reference listing BeautifIcon's
   icon options.
"""

from pytopo import MapUtils

import folium
use_beautify = True
if use_beautify:
    from folium.plugins import BeautifyIcon

from math import pi


# First pair is what the photo says, from jhead or exiftool;
# second pair is actual loc from pytopo.
photo_pts = [
    [ 'Frijoles upper crossing',
      ('N 35d 49m 11.35s', 'W 106d 20m 56.10s'),
      ('35.8152646',       '-106.3614038') ],

    # This one's weird: we don't see the red point plotted, because
    # the camera coordinates are exactly the same as the ones for
    # Tyuyoni Overlook (which isn't even from this same hike,
    # it was several weeks earlier).
    # We calculate 0.5007 mi at bearing 307
    # https://www.movable-type.co.uk/scripts/latlong.html calculates:
    # Distance: 	0.8058 km  --> 0.50070091 mi NW
    # Initial bearing: 	126° 35′ 23″
    # Final bearing: 	126° 35′ 39″
    # Midpoint: 	35° 46′ 54″ N, 106° 16′ 30″ W
    [ 'tarantula near Bandelier Visitor Center',
      ('N 35d 47m  1.62s', 'W 106d 16m 42.50s'),
      ('35.7794636',       '-106.2713003') ],

    # Tyuyoni Overlook: we calculate 0.1603 miles difference, SW (227)
    # gmap-pedometer.com says it's .1645 miles
    # https://www.movable-type.co.uk/scripts/latlong.html says:
    # Distance: 	0.2579 km (to 4 SF*)  --> 0.16025163 mi
    # Initial bearing: 	046° 55′ 00″
    # Final bearing: 	046° 55′ 05″
    # Midpoint: 	35° 47′ 04″ N, 106° 16′ 39″ W
    [ 'Tyuyoni Overlook',
      ('N 35d 47m  1.62s', 'W 106d 16m 42.50s'),
      ('35.7853676',       '-106.2763840') ],

    # we calculate 0.7982 mi WSW (244°)
    # .8422 mi acc to gmaps-ped
    # movable type says
    # Distance: 	1.398 km (to 4 SF*)
    # Initial bearing: 	243° 38′ 12″
    # Final bearing: 	243° 37′ 43″
    # Midpoint: 	35° 47′ 12″ N, 106° 46′ 57″ W
    [ 'Stable Mesa top of death climb',
      ('N 35d 47m  1.62s', 'W 106d 47m 21.55s'),
      ('35.7893678'  ,     '-106.7754314') ],

    [ 'Kimberly Overlook',
      ('N 35d 48m  6.48s', 'W 106d 11m 29.38s'),
      ('35.8114868',       '-106.1989731') ],

    [ 'Foot of Potrero Falls',
      ('N 36d 24m 51.89s', 'W 106d 11m 40.29s'),
      ('36.4072927',       '-106.2058261') ],

    [ 'kiosk shed above Clayton Lake Dinosaur Trackway',
      ('N 36d 34m 35.67s', 'W 103d 17m 54.34s'),
      (36.5776572, -103.2963927) ],

    [ 'Trail down to Capulin Volcano crater vent',
      ('N 36d 46m 29.18s', 'W 103d 58m 11.22s'),
      ('36.7823963',       '-103.9718991') ],

    [ 'Raton Goat Hill',
      ('N 36d 54m  3.24s', 'W 104d 26m  3.44s'),
      ('36.9042233',       '-104.4449874') ],
]


def angle_octant(angle):
    """Given an angle in radians, return a direction string like N or SSW.
       Angle must be between 0 and 2*pi
       (as returned from haversine_angle).
    """
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = int((angle + 11.25)/22.5)
    return dirs[ix % 16]


def compare_points():
    m = folium.Map(control_scale=True)

    for point in photo_pts:
        name = point[0]
        cam_lat = MapUtils.to_decimal_degrees(point[1][0])
        cam_lon = MapUtils.to_decimal_degrees(point[1][1])
        real_lat = MapUtils.to_decimal_degrees(point[2][0])
        real_lon = MapUtils.to_decimal_degrees(point[2][1])

        dist = MapUtils.haversine_distance(real_lat, real_lon,
                                           cam_lat, cam_lon)
        angle = MapUtils.bearing(real_lat, real_lon, cam_lat, cam_lon)
        print(f"{name}: {dist:.3f} miles to the {angle_octant(angle)}"
              f" ({angle:.0f}°)\n")

        # Two different ways of showing icons in folium.
        # Neither of them has any documentation on what icons are available.

        if use_beautify:
            # Using BeautifyIcon:
            icon = BeautifyIcon(icon_shape='rectangle-dot',
                                border_width="5",
                                border_color='red')
            folium.Marker([cam_lat, cam_lon], tooltip=name + ' (camera)',
                          icon=icon).add_to(m)
            icon = BeautifyIcon(icon_shape='circle-dot',
                                border_width="5",
                                border_color='blue')
            folium.Marker([real_lat, real_lon], tooltip=name + ' (real)',
                          icon=icon).add_to(m)

        else:
            # Using FontAwesome:
            folium.Marker(location=[cam_lat, cam_lon], icon=folium.Icon(
                color='red', icon='camera', prefix='fa')).add_to(m)
            folium.Marker(location=[real_lat, real_lon], icon=folium.Icon(
                color='blue', icon='circle', prefix='fa')).add_to(m)

    m.fit_bounds(m.get_bounds())

    outfile = 'pixel-photos.html'
    m.save(outfile)
    print("Saved to", outfile)


if __name__ == '__main__':
    compare_points()


