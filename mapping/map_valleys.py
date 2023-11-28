#!/usr/bin/env python3

# Uses PySheds http://mattbartos.com/pysheds/

# Debian's pyproj can't figure out that it uses /usr/share/proj
# so you have to tell it to avoid a warning:
from os import environ
environ['PROJ_LIB'] = '/usr/share/proj/'


from pysheds.grid import Grid
import geojson
from geopy.distance import distance
from os.path import splitext
from sys import argv, float_info
# import matplotlib.pyplot as plt
import csv


branchfilename = "branches.geojson"
branchfilename = "branches-walnut-cyn.geojson"


demname = 'n35_w107_1arc_v3.tif'

# Just the area around Walnut Canyon
demname = 'n35_w107_1arc-extent-walnut-cyn.tif'
branchfilename = 'branches-walnut-cyn.gepjson'

# What Walnut Canyon will look like when read from GNIS
# feature_id|feature_name|feature_class|state_name|state_numeric|county_name|county_numeric|map_name|date_created|date_edited|bgn_type|bgn_authority|bgn_date|prim_lat_dms|prim_long_dms|prim_lat_dec|prim_long_dec|source_lat_dms|source_long_dms|source_lat_dec|source_long_dec
# 2772507|Walnut Canyon|Valley|New Mexico|35|Los Alamos|028|Guaje Mountain|10/21/2015|01/28/2020||||355319N|1061804W|35.8886516|-106.300982|355350N|1061836W|35.897271|-106.3100161
row = {'bgn_authority': '',
 'bgn_date': '',
 'bgn_type': '',
 'county_name': 'Los Alamos',
 'county_numeric': '028',
 'date_created': '10/21/2015',
 'date_edited': '01/28/2020',
 'feature_class': 'Valley',
 'feature_name': 'Walnut Canyon',
 'map_name': 'Guaje Mountain',
 'prim_lat_dec': '35.8886516',
 'prim_lat_dms': '355319N',
 'prim_long_dec': '-106.300982',
 'prim_long_dms': '1061804W',
 'source_lat_dec': '35.897271',
 'source_lat_dms': '355350N',
 'source_long_dec': '-106.3100161',
 'source_long_dms': '1061836W',
 'state_name': 'New Mexico',
 'state_numeric': '35',
 '\ufefffeature_id': '2772507'}

# Mouth and source of Walnut Canyon
# mouthy, mouthx = 35.893005, -106.304162
# sourcey, sourcex = 35.899166, -106.313400


# When selecting lines, one might prefer a match at the beginning of a line
# (for matching header points), at the end (for mouth points) or don't care.
from enum import Enum
class WhichEnd(Enum):
    NO_PREFERENCE = 0
    PREFER_TOP    = 1
    PREFER_BOTTOM = 2


def plotFigure(data, label, cmap='Blues'):
    plt.figure(figsize=(12,10))
    plt.imshow(data, cmap)
    plt.colorbar(label=label, shrink=0.6)
    plt.grid()
    plt.plot()
    plt.show()

# plotFigure(dem, 'Elevation (m)', 'terrain')


def map_branches(demname):
    """Use pysheds to analyze the input Digital Elevation Map and
       create a network of branched LineStrings representing drainages.
       Return a JSON FeatureList of branches,
       plus the list of connections between branches.
    """
    branchfilename = splitext(demname)[0] + '-branches.geojson'

    # Branches already written?
    # XXX But we also need to calculate grid.
    # try:
    #     with open(branchfilename) as fp:
    #         branches = geojson.load(fp)
    #         print("Read branches from", branchfilename)
    #         return branches
    # except FileNotFoundError:
    #     pass
    # except Exception as e:
    #     print("Problem opening", branchfilename, ": will regenerate it")

    # Read elevation raster
    # ----------------------------
    grid = Grid.from_raster(demname)
    dem = grid.read_raster(demname)

    # Condition DEM
    # ----------------------
    # Fill pits in DEM
    pit_filled_dem = grid.fill_pits(dem)

    # Fill depressions in DEM
    flooded_dem = grid.fill_depressions(pit_filled_dem)

    # Resolve flats in DEM
    inflated_dem = grid.resolve_flats(flooded_dem)

    # Determine D8 flow directions from DEM
    # ----------------------
    # Specify directional mapping
    # This apparently represents: N, NE, E, SE, S, SW, W, NW
    # and is the default.
    # Another possibility is (1, 2, 3, 4, 5, 6, 7, 8)
    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)

    # Compute flow directions
    # -------------------------------------
    fdir = grid.flowdir(inflated_dem, dirmap=dirmap)

    # Calculate flow accumulation
    # --------------------------
    acc = grid.accumulation(fdir, dirmap=dirmap)

    '''
    # Delineate a catchment
    # ---------------------
    # Specify pour point
    x, y = -97.294, 32.737

    # Snap pour point to high accumulation cell
    x_snap, y_snap = grid.snap_to_mask(acc > 1000, (x, y))

    # Delineate the catchment
    catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, 
                           xytype='coordinate')

    # Crop and plot the catchment
    # ---------------------------
    # Clip the bounding box to the catchment
    grid.clip_to(catch)
    clipped_catch = grid.view(catch)
    '''

    # Extract river network
    # ---------------------
    branches = grid.extract_river_network(fdir, acc > 50, dirmap=dirmap)

    # Save the river network, a large collection of LineStrings
    with open(branchfilename, "w") as fp:
        geojson.dump(branches, fp, indent=2)
        print("Wrote branches to", branchfilename)
        # fp.write(str(branches))

    # https://github.com/mdbartos/pysheds/issues/183
    # Get profiles and connections
    profiles, connections = grid.extract_profiles(fdir, acc > 50, dirmap=dirmap,
                                                  include_endpoint=True)
    '''Returns (from help(grid.extract_profiles):
    profiles : list of lists of ints
               A list containing a collection of river profiles. Each
               river profile is a list containing the indices of the
               grid cells inside the river segment. Indices correspond
               to the flattened index of river segment cells.
    connections : dict (int : int)
                  A dictionary describing the connectivity of the
                  profiles. For each key-value pair, the key
                  represents index of the upstream profile and the
                  value represents the index of the downstream profile
                  that it drains to. Indices correspond to the ordered
                  elements of the `profiles` object.
    '''

    return branches, connections


def nearest_line(point, lines, which_end=WhichEnd.NO_PREFERENCE):
    """Given a point (lat, lon), and a line list,
       Return index of line, distance from point to nearest point,
       index within line of nearest point

       This has to be done for every line, for every start and end point.
       Ouch! Hope eventually I can find a faster way.
    """
    # BEWARE: geopy.distance.distance takes (lat, lon) pairs.
    # geojson.feature.Feature lists coordinates as (lon, lat).
    # geopy.distance.distance units are km

    # This will be a list of (distance, lineindex, along_key)
    # where along_key is a sort key helper reflecting whether the
    # line conforms to the caller's which_end preference:
    # as a sort key, a low number means it will be preferred.
    distance_list = []

    print("total of", len(lines), "lines")
    for lindex, line in enumerate(lines):
        min_dist = float_info.max
        closest_line_index = None
        percent_along = None
        npoints = len(line["geometry"]["coordinates"])
        for i, (lon, lat) in enumerate(line["geometry"]["coordinates"]):
            dist = distance(point, (lat, lon))
            if dist < min_dist:
                min_dist = dist
                closest_line_index = i
                # Make along_key reflect which quarter of the line
                # the point is in
                if which_end == WhichEnd.PREFER_TOP:
                    along_key = int(4 * i / npoints)
                elif which_end == WhichEnd.PREFER_BOTTOM:
                    along_key = 4 - int(4 * i / npoints)
                else:
                    along_key = 2
                # closelat, closelon = lat, lon

        # Add the entry for this line to the distance list
        distance_list.append((min_dist, lindex, along_key, i))

    # Sort distance_list to decide which one to return.
    # If there are multiple entries of similar close
    print("distance_list[0]", distance_list[0][0])
    print("type", type(distance_list[0][0]))
    print("km", distance_list[0][0].km)
    distance_list.sort(key=lambda x: f'{x[2]} {float(x[0].km):.2f}')

    # TEMPORARY: to visualize this list, save a GPX file of the list.
#     with open("nearest_pts.gpx", 'w') as fp:
#         print('''<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
# <gpx version="1.1" creator="OsmAnd+" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
# ''', file=fp)
#         print(f'''  <wpt lat="{point[0]}" lon="{point[1]}">
#     <name>*** POINT ***</name>
#   </wpt>''', file=fp)
#         for d in distance_list:
#             dist, i, percent_along, coords = d
#             print(f'''  <wpt lat="{coords[0]}" lon="{coords[1]}">
#     <name>i={i}, ({dist.km:.02f}, &lt;{along_key}%gt;)</name>
#   </wpt>''', file=fp)
#         print('</gpx>', file=fp)
#         print("saved nearest_pts.gpx")

    # Return index of line, distance, index within line of closest point
    return distance_list[0][1], distance_list[0][0], distance_list[0][3]


def follow_downstream(startpoint, endpoint, branches, connections):
    """Given starting and ending points (latitude, longitude)
       plus "branches" and "connections" from pysheds,
       trace from the startpoint downstream to the place nearest
       the endpoint.
       Return a list of coordinate pairs (lon, lat).
    """
    lines = branches['features']
    startline, dist, starti = nearest_line(startpoint, lines,
                                           which_end=WhichEnd.PREFER_TOP)
    print("startline:", startline, "at distance:", dist)
    endline, dist, endi = nearest_line(endpoint, lines,
                                       which_end=WhichEnd.PREFER_BOTTOM)
    print("endline:", endline, "at distance:", dist)

    basin_points = []
    # print("start line:", lines[startline])
    # print("end line:", lines[endline])

    # Trace the stream segments downward:
    lineindex = startline

    # If the given start point is before the line (i.e. the closest point
    # on the line is the first point), then start with the given start point.
    # But sometimes, the start point is in the middle of the line segment;
    # in that case, rather than starting with the given point or the
    # point nearest it on the line, start with the beginning of that line
    # segment, because it doesn't hurt to show a valley starting a little early.
    if starti == 0:
        basin_points.append(startpoint)
    while True:
        for i, point in enumerate(lines[lineindex]['geometry']['coordinates']):
            basin_points.append(point)

            # Are we at the end of the last line segment?
            if lineindex == endline and i >= endi:
                # If the closest line point to the endpoint was the last
                # point in the line, then maybe the endpoint is even
                # farther downstream. In that case, connect it with a
                # straight line.
                if endi >= len(lines[lineindex]['geometry']['coordinates'])-1:
                    basin_points.append((endpoint[1], endpoint[0]))
                return basin_points

        # Done with line. Is it the last segment?
        if connections[lineindex] == lineindex:
            return basin_points

        # Move to the next line segment
        lineindex = connections[lineindex]


def trace_GNIS_valleys(GNISfile, branches, connections):
    """Parse a USGS GNIS CSV file, and
       using branches and connections from analyzing a DEM with PySheds,
       create JSON for the valley traces.
    """


if __name__ == '__main__':
    branches, connections = map_branches(argv[1])

    startpt = (float(row['source_lat_dec']), float(row['source_long_dec']))
    endpt = (float(row['prim_lat_dec']), float(row['prim_long_dec']))

    basin = follow_downstream(startpt, endpt, branches, connections)
    # print()
    # print("Basin:", basin)

    with open("valleys.gpx", 'w') as fp:
        print('''<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<gpx version="1.1" creator="OsmAnd+" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
''', file=fp)

        print(f'''  <wpt lat="{startpt[0]}" lon="{startpt[1]}">
    <name>*** {row['feature_name']} SOURCE ***</name>
  </wpt>''', file=fp)

        print(f'''  <wpt lat="{endpt[0]}" lon="{endpt[1]}">
    <name>*** {row['feature_name']} MOUTH ***</name>
  </wpt>''', file=fp)

        print('  <trk>', file=fp)
        print(f'    <name>{row["feature_name"]}</name>', file=fp)
        print('    <trkseg>', file=fp)

        for coords in basin:
            print(f'''      <trkpt lat="{coords[1]}" lon="{coords[0]}">
      </trkpt>''', file=fp)

        print('''    </trkseg>\n  </trk>\n''', file=fp)

        print('</gpx>', file=fp)
        print("saved valleys.gpx")
