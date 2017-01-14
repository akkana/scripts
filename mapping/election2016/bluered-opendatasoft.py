#!/usr/bin/env python

# Plot blue-red-purple election results for the 2016 presidential election.

# Expects the following data files:
# data/state-shapes/st99_d00* from mpl basemap examples directory
#   (/usr/share/doc/python-mpltoolkits.basemap-doc/examples/ on debian
#    or https://github.com/matplotlib/basemap/blob/master/examples/ )
# data//Deleetdk/counties-opendatasoft-2016.csv from
#   https://public.opendatasoft.com/explore/dataset/usa-2016-presidential-election-by-county/export/
#  (full URL:
#   https://public.opendatasoft.com/explore/dataset/usa-2016-presidential-election-by-county/download/?format=csv&timezone=America/Denver&use_labels_for_header=true )

# Copyright Akkana Peck under the GPLv2 or later, share and enjoy.

# Good tutorial that explains the args (unlike the Basemap doc):
# http://www.datadependence.com/2016/06/creating-map-visualisations-in-python/

import sys

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

# We need CSV to parse the county data:
import csv
# but then the county shapes are encoded inside the CSV as JSON, so
import simplejson as json

def map_from_bounding_box(bbox):
    '''Draws a map from a bounding box that's a dict with
       lllon, lllat, urlon, urlat.
    '''
    centerlon = float(bbox['lllon'] + bbox['urlon']) / 2.0
    centerlat = float(bbox['lllat'] + bbox['urlat']) / 2.0

    m = Basemap(resolution='i',  # crude, low, intermediate, high, full
                llcrnrlon = bbox['lllon'], urcrnrlon = bbox['urlon'],
                lon_0 = centerlon,
                llcrnrlat = bbox['lllat'], urcrnrlat = bbox['urlat'],
                lat_0 = centerlat,
                projection='tmerc')

    # map.drawmapboundary(fill_color='ivory')
    # map.fillcontinents(color='coral', lake_color='aqua')

    # m.drawcoastlines()
    # m.drawcountries()

    # drawstates() is built into basemap -- but then there's no
    # way to associate the shapes with state names. Hence the shape files.
    # m.drawstates()

    # draw state boundaries.
    # data from U.S Census Bureau
    # http://www.census.gov/geo/www/cob/st2000.html
    shp_info = m.readshapefile('data/state-shapes/st99_d00','states',
                               drawbounds=True)

    # Wouldn't it be nice if there was documentation anywhere on what
    # readshapefile() does? But there isn't, so:
    # After readshapefile(), m will have two new members:
    #
    # m.states_info[] is a list of dicts with the following useful info:
    # NAME, AREA, PERIMETER
    # plus the following arcane and undocumented members:
    # DIVISION, RINGNUM, REGION, LSAD, LSAD_TRANS,
    # STATE, ST99_D00_I, SHAPENUM, ST99_D00_
    #
    # m.states[] is a list of lists of 2-tuples of numbers, not coordinates,
    # like (-745649.3757546246, 6074729.819906185).
    #
    # If you want to do anything with the shapes by state name,
    # you have to iterate through m.states_info looking for the name,
    # note the index, then use that same index into m.states.

    return m

def map_county_data(m):
    '''
    '''
    # fp = open("data/alamos.csv")
    csv.field_size_limit(sys.maxsize)
    fp = open("data/Deleetdk/counties-opendatasoft-2016.csv")
    reader = csv.DictReader(fp, delimiter=';')

    ax = plt.gca() # get current axes instance

    for county in reader:
        # print county["County"], county["State"]
        try:
            countyshape = json.loads(county["Geo Shape"])
            shapecoords = countyshape["coordinates"]
        except Exception, e:
            # Some fields don't have GeoShape in this file, like in Alaska.
            print county["County"], county["State"], \
                ": No GeoShape. Or something:", e
            continue

        # What color is this county?
        dem = float(county["Clinton H"])
        rep = float(county["Trump D"])
        # pop = float(county["Total.Population"])
        pop = float(county["votes"])
        # print county["County"], ":", dem, rep, pop, county["votes"]
        blue = dem/pop
        red = rep/pop
        color = (red, 0, blue)

        # Some counties have a list of lists of coordinate pairs,
        # a few big ones have a list of lists of lists of pairs.
        # So we need to factor the handling of the final list:
        def handle_subregion(subregion):
            for coord_pair in subregion:
                coord_pair[0], coord_pair[1] = m(coord_pair[0], coord_pair[1])

            poly = Polygon(subregion, facecolor=color, edgecolor=color)
            ax.add_patch(poly)

        if countyshape["type"] == "Polygon":
            for subregion in shapecoords:
                handle_subregion(subregion)
        elif countyshape["type"] == "MultiPolygon":
            for subregion in shapecoords:
                for sub1 in subregion:
                    handle_subregion(sub1)
        else:
            print "Skipping", county["County"], \
                "because of unknown type", countyshape["type"]

def init_map():
    '''Draw a map of the US, upon which we can graph county results.
    '''
    bbox = { 'lllon': -119, 'urlon': -64, 'lllat': 22.0, 'urlat': 50. }

    m = map_from_bounding_box(bbox)

    return m

def show_map():
    # This gets rid of most of the extra horizontal whitespace,
    # and about half the vertical:
    plt.tight_layout(pad=0, w_pad=0, h_pad=0)

    plt.title('The Map')
    plt.show()
    # plt.savefig('test.png')

if __name__ == "__main__":
    m = init_map()

    map_county_data(m)

    show_map()
