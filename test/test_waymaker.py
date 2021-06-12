#!/usr/bin/env python3

import unittest

import os
import shutil

from mapping import waymaker


TMPDIR = '/tmp/test-waymaker'


class TestWaymaker(unittest.TestCase):
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
        self.assertEqual(entries, [
            [35.825485, -106.21147, '10 Sherwood Blvd, White Rock, NM 87547\nWhite Rock Library'],
            [35.88126, -106.29589, '1000 Central Ave\nLos Alamos, NM 87544\nLos Alamos County Building\nand also Council Headquarters']])

        gpxfile = os.path.join(TMPDIR, "test-ways.gpx")
        waymaker.write_gpx_file(entries, gpxfile, omit_time=True)

        with open(gpxfile) as gpxfp:
            written_gpx = gpxfp.read()
            self.assertEqual(written_gpx, '''<?xml version="1.0" encoding="UTF-8"?>
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

