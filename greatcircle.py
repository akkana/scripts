#!/usr/bin/env python3

# Given start lat/lon and end lat/lon, calculate the initial heading
# needed to fly from the start to the end point on a great circle course,
# and the final heading on which you'll arrive.
# Based on spreadsheet equations by Galen Gisler, from the Wikipedia
# page on great circle navigation,
# https://en.wikipedia.org/wiki/Great-circle_navigation#Course

import sys
from math import radians, degrees, sin, cos, atan2, sqrt

def flyto(lat1, lon1, lat2, lon2):
    """Return initial heading, final heading when flying from (lat1, lon1)
       to (lat2, lon2) on a great circle course.
    """
    # Convert everything to radians
    d3_lat1 = radians(lat1)
    e3_lon1 = radians(lon1)
    d4_lat2 = radians(lat2)
    e4_lon2 = radians(lon2)

    e5_dlon = e4_lon2 - e3_lon1

    f3_num1 = cos(d4_lat2) * sin(e5_dlon)
    g3_denom1 = cos(d3_lat1) * sin(d4_lat2) \
        - sin(d3_lat1) * cos(d4_lat2) * cos(e5_dlon)

    f4_num2 = cos(d3_lat1) * sin(e5_dlon)
    g4_denom2 = sin(d4_lat2) * cos(d3_lat1) * cos(e5_dlon) \
        - cos(d4_lat2) * sin(d3_lat1)

    f6_cd_num = sqrt(g3_denom1**2 + f3_num1**2)
    g6_cd_denom = sin(d3_lat1) * sin(d4_lat2) \
        + cos(d3_lat1) * cos(d4_lat2) * cos(e5_dlon)

    # Python atan2 takes args in the opposite order to spreadsheets
    e6_cd_rad = atan2(f6_cd_num, g6_cd_denom)
    # c6_cd_deg = degrees(e6_cd_rad)

    d7_init_heading_rad = atan2(f3_num1, g3_denom1)
    d8_final_heading_rad = atan2(f4_num2, g4_denom2)

    return degrees(d7_init_heading_rad), degrees(d8_final_heading_rad)


if __name__ == '__main__':
    init_heading, final_heading = flyto(*[ float(s) for s in sys.argv[1:] ])

    print("Initial heading: %f" % init_heading)
    print("  Final heading: %f" % final_heading)

