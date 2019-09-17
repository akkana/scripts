#!/usr/bin/env python3

# Take the shapefile of New Mexico voting precincts, which are labeled
# according to which house, senate and uscong district each precinct is in,
# and create a file of the house, senate or uscong districts.
#
# Pass in the path to the .shp file.
# Geojson input seems to work, but alas, writing to geojson output doesn't
# because apparently fiona has some sort of confusion between
# MultiPolygon and Polygone:
# fiona.errors.GeometryTypeValidationError: Record's geometry type does not
# match collection schema's geometry type: 'MultiPolygon' != 'Polygon'
#
# This process of coalescing lots of small shapes into a smaller number
# of larger shapes is for some reason called "dissolving".
#
# Get the precinct shapefile from: http://rgis.unm.edu/rgis6/
# ... click on Boundaries, the Voting Districts.

# Share and enjoy (or modify for your own state's situation)
# under the GPLv2 or, at your option, a later GPL.

# Thanks to
# https://gis.stackexchange.com/questions/149959/dissolving-polygons-based-on-attributes-with-python-shapely-fiona

from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import fiona
import itertools
from collections import OrderedDict
import sys, os

def Usage():
    print("Usage: %s filename senate|house|uscong"
          % os.path.basename(sys.argv[0]))
    sys.exit(1)

try:
    infile = sys.argv[1]
except:
    Usage()

bname, dname = os.path.split(infile)

for whichhouse in ('house', 'senate', 'uscong'):
    print("======", whichhouse)

    outfile = '%s_%s' % (whichhouse, dname)
    if bname:
        outfile = os.path.join(bname, outfile)

    groupfield = whichhouse + '_dis'

    # Alas, the fields are inconsistent: house_dist, senate_is, uscong_dis
    if whichhouse == 'house':
        groupfield += 't'

    label = whichhouse.capitalize()

    with fiona.open(infile) as input:
        # preserve the schema of the original shapefile, including the crs
        meta = input.meta
        meta['schema']['properties'] = OrderedDict([('NAME10', 'str:100'),
                                                    ('precincts', 'str:400')])

        with fiona.open(outfile, 'w', **meta) as output:
            # groupby clusters consecutive elements of an iterable that have the
            # same key so you must first sort the features by the desired field
            # To group by more than one field you can do something like:
            # e = sorted(input, key=lambda k: (k['properties']['FIELD_1'],
            #                                  k['properties']['FIELD_2']) )
            e = sorted(input, key=lambda k: k['properties'][groupfield])
            # group by the requested field
            for key, group in itertools.groupby(e,
                                  key=lambda x:x['properties'][groupfield]):
                properties, geom = zip(*[(feature['properties'],
                                          shape(feature['geometry']))
                                         for feature in group])

                precincts = [ prop['prec_num'] for prop in properties ]
                precincts.sort()

                # Apparently the name of the region should have key 'NAME10'.
                # I don't know why.
                newproperties = {
                    'NAME10': '%s District %d' % (label, properties[0][groupfield]),
                    'precincts': ','.join([ str(p) for p in precincts ])
                }

                # write the feature, computing the unary_union of the elements in the group with the properties of the first element in the group
                # output.write({'geometry': mapping(unary_union(geom)), 'properties': properties[0]})
                output.write({
                    'geometry': mapping(unary_union(geom)),
                    'properties': newproperties
                })



