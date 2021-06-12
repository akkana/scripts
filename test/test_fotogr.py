#!/usr/bin/env python3

import unittest

import shutil
import os

import fotogr

TMPDIR = '/tmp/test-fotogr'

class TestFotogr(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TMPDIR):
            shutil.rmtree(TMPDIR)
        os.mkdir(TMPDIR)
        print("\n\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMPDIR)
        pass

    @staticmethod
    def make_empty_file(filepath):
        with open(os.path.join(TMPDIR, filepath), "w") as fp:
            print(' ', file=fp)
            # Okay, so it's not strictly empty

    def test_fotogr(self):
        with open(os.path.join(TMPDIR, "Tags"), "w") as tagfp:
            print("""
category Tags

tag testcase : a.jpg b.jpg

tag TestCase : A.jpg B.jpg

tag AAA : a.jpg A.jpg

tag ponies : subdir/pony.jpg
""", file=tagfp)

        TestFotogr.make_empty_file("a.jpg")
        TestFotogr.make_empty_file("b.jpg")
        TestFotogr.make_empty_file("A.jpg")
        TestFotogr.make_empty_file("B.jpg")

        # And a subdirectory
        subdir = os.path.join(TMPDIR, "subdir")
        os.mkdir(subdir)
        TestFotogr.make_empty_file(os.path.join(subdir, "pony.jpg"))
        TestFotogr.make_empty_file(os.path.join(subdir, "chicken.jpg"))

        with open(os.path.join(subdir, "Tags"), "w") as tagfp:
            print("""
category Tags

tag chickens : chicken.jpg
""", file=tagfp)

        # Test several OR options
        r = list(fotogr.search_for_keywords([TMPDIR], ["testcase"],
                                            [], [], True))
        self.assertEqual(r, [os.path.join(TMPDIR, 'a.jpg'),
                             os.path.join(TMPDIR, 'b.jpg'),
                             os.path.join(TMPDIR, 'A.jpg'),
                             os.path.join(TMPDIR, 'B.jpg')])

        r = list(fotogr.search_for_keywords([TMPDIR], ["testcase"],
                                            [], [], False))
        self.assertEqual(r, [os.path.join(TMPDIR, 'a.jpg'),
                             os.path.join(TMPDIR, 'b.jpg')])

        r = list(fotogr.search_for_keywords([TMPDIR], ["TestCase"],
                                            [], [], False))
        self.assertEqual(r, [os.path.join(TMPDIR, 'A.jpg'),
                             os.path.join(TMPDIR, 'B.jpg')])

        # ignorecase=True
        r = list(fotogr.search_for_keywords([TMPDIR], ["TestCase"],
                                            [], [], True))
        self.assertEqual(r, [os.path.join(TMPDIR, 'a.jpg'),
                             os.path.join(TMPDIR, 'b.jpg'),
                             os.path.join(TMPDIR, 'A.jpg'),
                             os.path.join(TMPDIR, 'B.jpg')])

        # Test NOT option
        r = list(fotogr.search_for_keywords([TMPDIR],
                                            ['testcase'],
                                            [],
                                            ['AAA'],
                                            False))
        self.assertEqual(r, [os.path.join(TMPDIR, 'b.jpg')])

        # NOT and ignorecase
        r = list(fotogr.search_for_keywords([TMPDIR],
                                            ['testcase'],
                                            [],
                                            ['AAA'],
                                            True))
        self.assertEqual(r, [os.path.join(TMPDIR, 'b.jpg'),
                             os.path.join(TMPDIR, 'B.jpg')])

        # Test subdirs
        r = list(fotogr.search_for_keywords([TMPDIR],
                                            ['ponies', 'chickens'],
                                            [], [], False))
        self.assertEqual(r, [os.path.join(subdir, 'pony.jpg'),
                             os.path.join(subdir, 'chicken.jpg')])

        r = list(fotogr.search_for_keywords([TMPDIR],
                                            ['ponies', 'chickens', "AAA"],
                                            [], [],
                                            False))
        self.assertEqual(r, [os.path.join(TMPDIR, 'a.jpg'),
                             os.path.join(TMPDIR, 'A.jpg'),
                             os.path.join(subdir, 'pony.jpg'),
                             os.path.join(subdir, 'chicken.jpg')])

        r = list(fotogr.search_for_keywords([TMPDIR],
                                            [],
                                            ['ponies', 'chickens'],
                                            [], False))
        self.assertEqual(r, [])


if __name__ == '__main__':
    unittest.main()

