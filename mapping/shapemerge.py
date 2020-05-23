#!/usr/bin/env python3

# Take a shapefile of lots of small shapes, like voting precincts
# or counties, and create different shapes according to some attribute.
# For instance, in a shapefile of San Juan county, NM voting precincts,
# create a new shapefile with shappes according to the Comm_Dist attribute.
#
# Pass in the path to the .shp file, and the name of the desired attribute.
# Geojson input seems to work, but alas, writing to geojson output doesn't
# because apparently fiona has some sort of confusion between
# MultiPolygon and Polygone:
# fiona.errors.GeometryTypeValidationError: Record's geometry type does not
# match collection schema's geometry type: 'MultiPolygon' != 'Polygon'
#
# This process of coalescing lots of small shapes into a smaller number
# of larger shapes is for some reason called "dissolving".
#

# Copyright 2020 by Akkana Peck. Share and enjoy under the GPLv2 or later.

# Thanks to
# https://gis.stackexchange.com/questions/149959/dissolving-polygons-based-on-attributes-with-python-shapely-fiona

from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import fiona
import itertools
from collections import OrderedDict
import argparse
import sys, os


parser = argparse.ArgumentParser(
    description="Dissolve shapes in a GIS file according to " \
                "a specified attribute")

parser.add_argument('-k', '--key', dest='inkey', default='OBJECTID',
                    help="Identifier in the input file: the key that will be used for the dissolve")
parser.add_argument('-K', '--outputkey', dest='outkey', default='NAME10',
                    help="The key in the output file for the identifiers seen in the input key")

parser.add_argument('infile', help="The input shapefile")
parser.add_argument('outfile', nargs='?', help="output file")

args = parser.parse_args(sys.argv[1:])

if not args.outfile:
    args.outfile = args.inkey
while args.infile.startswith(args.outfile):
    args.outfile += '-merge'


with fiona.open(args.infile) as input:
    # preserve the schema of the original shapefile, including the crs
    meta = input.meta
    meta['schema']['properties'] = OrderedDict([(args.outkey, 'str:100'),
                                                ('components', 'str:400')])

    with fiona.open(args.outfile, 'w', **meta) as output:
        # groupby clusters consecutive elements of an iterable that have the
        # same key, so you must first sort the features by the desired field.
        sorted_shapes = sorted(input, key=lambda k:
                                k['properties'][args.inkey])

        # Group by the requested field, and loop over the groups.
        for key, group in itertools.groupby(sorted_shapes,
                              key=lambda x:x['properties'][args.inkey]):
            properties, geom = zip(*[(feature['properties'],
                                      shape(feature['geometry']))
                                     for feature in group])

            # Which precincts went into this district group?
            # We'll maintain that list, sorted and comma separated,
            # under the key 'components'.
            precincts = [ prop[args.inkey] for prop in properties ]
            precincts.sort()

            newproperties = {
                args.outkey: properties[0][args.inkey],
                'components': ','.join([ str(p) for p in precincts ])
            }

            # write the feature, computing the unary_union of the elements
            # in the group with the properties of the first element in the group
            output.write({
                'geometry': mapping(unary_union(geom)),
                'properties': newproperties
            })

        print(f"Merged by key {args.inkey} to output key {args.outkey}; "
              f"wrote to {args.outfile}")



