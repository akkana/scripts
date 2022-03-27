#!/usr/bin/env python3

# Given a geojson that has two tags of interest, split by one of
# those tags. For instance, the NM SOS county commission district
# GIS has all counties in one file, with tags DIST_NUM and COUNTY,
# and it's useful to split by COUNTY into a file per county.
# Also replace DIST_NUM with DIST.

import json
import sys, os


REAL_TARGET = "DIST"


def split_geojson(infile: str, splitprop: str, targetprop=None):
    created_files = set()

    with open(infile) as infp:
        bigjson = json.loads(infp.read())

    basedir = os.path.dirname(os.path.abspath(infile))
    newdir = os.path.join(basedir, splitprop)
    if not os.path.isdir(newdir):
        os.makedirs(newdir)

    for feature in bigjson["features"]:
        propfilename = feature["properties"][splitprop].replace(' ', '_') \
            + ".json"
        propfile = os.path.join(newdir, propfilename)
        if not os.path.exists(propfile):
            print(f"Created {splitprop}/{propfilename}")
            with open(propfile, "w") as propfp:
                print("""{
  "type": "FeatureCollection",
"name": "Hoo Haw",
"crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::4269" } },
  "features": [
""", file=propfp)
            created_files.add(propfile)

        if targetprop:
            feature["properties"][REAL_TARGET] \
                = feature["properties"][targetprop]
            del feature["properties"][targetprop]

        with open(propfile, "a") as propfp:
            print(json.dumps(feature, indent=4) + ",", file=propfp)

    # Now close out all the files that were created
    for f in created_files:
        with open(f, "a") as propfp:
            print("]\n}", file=propfp)


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
        print(f"Usage: {os.path.basename(sys.argv[0])} "
              "filename splitprop [targetprop]")
        print("splitprop:  make separate files based on this property")
        print("targetprop: rename this property to DIST")
        sys.exit(1)

    infile = sys.argv[1]
    splitprop = sys.argv[2]
    if len(sys.argv) > 3:
        targetprop = sys.argv[3]
    else:
        targetprop = None
    split_geojson(infile, splitprop, targetprop=targetprop)

