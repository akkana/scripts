#!/usr/bin/env python

# Plot blue-red-purple election results for the 2016 presidential election.

# Expects the following data files:
# data/state-shapes/st99_d00* from mpl basemap examples directory
#   (/usr/share/doc/python-mpltoolkits.basemap-doc/examples/ on debian
#    or https://github.com/matplotlib/basemap/blob/master/examples/ )
# data/census-counties-2015/cb_2015_us_county_500k from
#   http://www.census.gov/geo/maps-data/data/cbf/cbf_counties.html
# data/Deleetdk/tidy_data.csv from
#   https://github.com/Deleetdk/USA.county.data/tree/master/inst/ext

# Copyright Akkana Peck under the GPLv2 or later, share and enjoy.

# Good tutorial that explains the args (unlike the Basemap doc):
# http://www.datadependence.com/2016/06/creating-map-visualisations-in-python/

import sys

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from difflib import SequenceMatcher

# We need CSV to parse the county data:
import csv
# but then the county shapes are encoded inside the CSV as JSON, so
import simplejson as json

def draw_us_map():
    # Set the lower left and upper right limits of the bounding box:
    lllon = -119
    urlon = -64
    lllat = 22.0
    urlat = 50.5
    # and calculate a centerpoint, needed for the projection:
    centerlon = float(lllon + urlon) / 2.0
    centerlat = float(lllat + urlat) / 2.0

    m = Basemap(resolution='i',  # crude, low, intermediate, high, full
                llcrnrlon = lllon, urcrnrlon = urlon,
                lon_0 = centerlon,
                llcrnrlat = lllat, urcrnrlat = urlat,
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
    shp_info = m.readshapefile('data/state-shapes/st99_d00', 'states',
                               drawbounds=True, color="lightgrey")

    # County data from Census Bureau
    shp_info = m.readshapefile('data/census-counties-2015/cb_2015_us_county_500k',
                               'counties',
                               drawbounds=False)

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

    # County shapes in the census shapefiles don't include the state name.
    # Instead, m.county_info[m]["STATEFP"] is an integer that corresponds
    # to some state's m.states_info[n]["STATE"].
    # So we need to build a table so we can look up state names
    # by their STATEFP.
    # For some reason, STATEFP goes up to 72. Go figure.
    maxstatefp = 0
    states = [None] * 75
    for state in m.states_info:
        statefp = int(state["STATE"])
        # print statefp, state["NAME"]
        if statefp > maxstatefp:
            maxstatefp = statefp
        # Many states have multiple entries in m.states (because of islands?).
        # Only need to add it once.
        if not states[statefp]:
            states[statefp] = state["NAME"]

    # print "max statefp:", maxstatefp
    # for i, s in enumerate(states):
    #     if s:
    #         print i, s

    return m, states

def map_county_data(m, states):
    '''
    '''
    # fp = open("data/alamos.csv")
    # csv.field_size_limit(sys.maxsize)
    fp = open("data/Deleetdk/tidy_data.csv")
    reader = csv.DictReader(fp)

    ax = plt.gca()     # get current axes instance

    # Make a dictionary of all counties and their colors.
    county_colors = {}
    for county in reader:
        # What color is this county?

        # Alaska has no results at all:
        if not county["results.clintonh"] or not county["results.trumpd"]:
            print "No results for", cname
            continue

        # print "keys:", county.keys()
        # The dataset holds at least one blank county in Alaska ...
        # which nevertheless has lots of demographic stats,
        # though no election results.
        if not county["name"]:
            # Alaska counties are all missing their county name,
            # but we might be able to get it from the longer County field.
            cname = county["County"][:-8]
            if cname.endswith(" Census Area"):
                cname = cname[:-12]
            elif cname.endswith(" City and Borough"):
                cname = cname[:-17]
            elif cname.endswith(" Borough"):
                cname = cname[:-8]
            else:
                print "Not sure what", cname, "ends with"
                continue
            print "County name was blank, using", cname
        else:
            cname = county["name"]

        # What color is this county?
        # print "keys:", county.keys()
        # print county
        dem = float(county["results.clintonh"])
        rep = float(county["results.trumpd"])
        # pop = float(county["Total.Population"])
        pop = float(county["votes"])
        # print county["name"], ":", dem, rep, pop, county["votes"]
        blue = dem/pop
        red = rep/pop

        # In the Deleetdk data, some counties end with "County" inappropriately.
        # Remove it, if so.
        if cname.lower().endswith(" county"):
            print "Stripping -county", cname
            cname = cname[:-7]
        county_colors["%s, %s" % (cname, county["State"])] \
            = (red, 0, blue)

    fp.close()

    # Now loop through all counties on the map, coloring them appropriately.
    for i, county in enumerate(m.counties_info):
        countyname = county["NAME"]
        try:
            statename = states[int(county["STATEFP"])]
        except IndexError:
            print countyname, "has out-of-index statefp of", county["STATEFP"]
            continue

        # The file has no results for Puerto Rico and Alaska.
        if statename == "Puerto Rico" or statename == "Alaska":
            continue

        if not statename:
            print "No state for", countyname
            continue

        countystate = "%s, %s" % (countyname, statename)

        try:
            ccolor = county_colors[countystate]
        except KeyError:
            # No exact match. Try for a fuzzy match.
            # Some counties in the Deleetdk are capitalized,
            # lack spaces between words, lack tildes or similar.
            fuzzyname = fuzzy_find(countystate, county_colors.keys())
            if fuzzyname:
                print "Got a fuzzy match,", countystate, "=", fuzzyname
                ccolor = county_colors[fuzzyname]
                county_colors[countystate] = ccolor
            else:
                print "No match for", countystate
                continue
        countyseg = m.counties[i]

        # Move Hawaii and Alaska:
        # http://stackoverflow.com/questions/39742305/how-to-use-basemap-python-to-plot-us-with-50-states
        # Offset Alaska and Hawaii to the lower-left corner.
        if statename == 'Alaska':
        # Alaska is too big. Scale it down to 35% first, then transate it.
            countyseg = list(map(lambda (x,y): (0.35*x + 1100000, 0.35*y-1300000), countyseg))
        elif statename == 'Hawaii':
            countyseg = list(map(lambda (x,y): (x + 5750000, y-1400000), countyseg))

        poly = Polygon(countyseg, facecolor=ccolor)  # edgecolor="white"
        ax.add_patch(poly)

def fuzzy_find(s, slist):
    '''Try to find a fuzzy match for s in slist.
    '''
    best_ratio = -1
    best_match = None

    ls = s.lower()
    for ss in slist:
        r = SequenceMatcher(None, ls, ss.lower()).ratio()
        if r > best_ratio:
            best_ratio = r
            best_match = ss
    if best_ratio > .75:
        return best_match
    return None

def init_map():
    '''Draw a map of the US, upon which we can graph county results.
    '''
    m, states = draw_us_map()

    # for i, shapedict in enumerate(m.states_info):
    #     statename = shapedict['NAME']
    #     if statename == "New Mexico":
    #         seg = m.states[i]
    #         # poly = Polygon(seg, facecolor='red', edgecolor='red')
    #         # ax.add_patch(poly)

    return m, states

def show_map():
    # This gets rid of most of the extra horizontal whitespace,
    # and about half the vertical:
    plt.tight_layout(pad=0, w_pad=0, h_pad=0)

    plt.title('The Map')
    plt.show()
    # plt.savefig('test.png')

if __name__ == "__main__":
    m, states = init_map()

    map_county_data(m, states)

    show_map()
