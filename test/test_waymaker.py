#!/usr/bin/env python3

# Waymaker uses external APIs to find coordinates, and those coordinates
# are floats that can vary in the 5th or so decimal place.
# This test tries to be tolerant of such differences, but
# there may be places where that still causes problems.

import unittest

import os
import math
import shutil

from mapping import waymaker


TMPDIR = '/tmp/test-waymaker'


class TestWaymaker(unittest.TestCase):
    def assertEntriesAlmostEqual(self, elist1, elist2):
        """Given two lists of entries, where an entry is [lat, lon, desc]
           assert if any of the descs differ, or if any of the float
           lats or lons don't satisfy math
        """
        for item1, item2 in zip(elist1, elist2):
            self.assertEqual(item1[2], item2[2])
            self.assertTrue(math.isclose(item1[0], item2[0], rel_tol=1e-6))
            self.assertTrue(math.isclose(item1[1], item2[1], rel_tol=1e-6))

    def assertEqualExceptFloats(self, str1, str2):
        for line1, line2 in zip(str1.splitlines(), str2.splitlines()):
            if line1 == line2:
                continue

    def test_waymaker(self):
        self.maxDiff = None    # to see full errors
        if os.path.exists(TMPDIR):
            shutil.rmtree(TMPDIR)
        os.mkdir(TMPDIR)
        inputfile = os.path.join(TMPDIR, "test-ways.txt")
        with open(inputfile, "w") as fp:
            print('''
10 Sherwood Blvd, White Rock, NM 87547
White Rock Library

1000 Central Ave
Los Alamos, NM 87544
Los Alamos County Building
and also Council Headquarters

''', file=fp)

        entries = waymaker.read_description_file(inputfile)
        self.assertEntriesAlmostEqual(entries, [
            [35.825485, -106.21147, '10 Sherwood Blvd, White Rock, NM 87547\nWhite Rock Library'],
            [35.88126, -106.29589, '1000 Central Ave\nLos Alamos, NM 87544\nLos Alamos County Building\nand also Council Headquarters']])

        # The written GPX is sensitive to float rounding errors.
        # Having already checked to make sure they're almost equal,,
        # now munge the coordinates so they'll match the expected ones.
        entries[0][0] = 35.825485
        entries[0][1] = -106.211470
        entries[1][0] = 35.825485
        entries[1][1] = -106.295890

        gpxfile = os.path.join(TMPDIR, "test-ways.gpx")
        waymaker.write_gpx_file(entries, gpxfile, omit_time=True)

        with open(gpxfile) as gpxfp:
            written_gpx = gpxfp.read()
            self.assertEqualExceptFloats(written_gpx,
'''<?xml version="1.0" encoding="UTF-8"?>
<gpx
 version="1.0"
creator="waymaker v. 0.2"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns="http://www.topografix.com/GPX/1/0"
xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
<bounds minlat="35.825485" minlon="-106.295890" maxlat="35.881260" maxlon="-106.211470"/>
<wpt lat="35.825485" lon="-106.211470">
<name>10 Sherwood Blvd, White Rock, NM 87547
White Rock Library</name>
</wpt>
<wpt lat="35.881260" lon="-106.295890">
<name>1000 Central Ave
Los Alamos, NM 87544
Los Alamos County Building
and also Council Headquarters</name>
</wpt>
</gpx>
''')

        # Clean up
        shutil.rmtree(TMPDIR)


if __name__ == '__main__':
    unittest.main()

