#!/usr/bin/env python3

"""Delete all <extensions> inside a GPX file,
   which OsmAnd likes to add on every waypoint and every trackpoint.
"""

from bs4 import  BeautifulSoup, element
import sys


def delete_extensions(gpxfile):
    with open(gpxfile) as fp:
        soup = BeautifulSoup(fp, features="xml")

    for feature in soup.find_all(['trkpt', 'wpt']):
        ext = feature.find('extensions')
        if type(ext) is element.Tag:
            ext.decompose()

    outfilename = gpxfile + '.fixed'
    with open(outfilename, 'w') as fp:
        # str(soup) has no indentation, but is otherwise good.
        # prettify() adds indentation but also adds way too many
        # extra line breaks. For now, live without the indentation.
        # fp.write(soup.prettify(formatter='minimal'))
        fp.write(str(soup))
        print("Wrote to", outfilename)


if __name__ == '__main__':
    for fil in sys.argv[1:]:
        delete_extensions(fil)

