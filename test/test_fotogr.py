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
    def make_empty_file(filename):
        with open(os.path.join(TMPDIR, filename), "w") as fp:
            print(' ', file=fp)

    def test_fotogr(self):
        with open(os.path.join(TMPDIR, "Tags"), "w") as tagfp:
            print("""
category Tags

tag testcase : a.jpg b.jpg

tag TestCase : A.jpg B.jpg""", file=tagfp)

        TestFotogr.make_empty_file("a.jpg")
        TestFotogr.make_empty_file("b.jpg")
        TestFotogr.make_empty_file("A.jpg")
        TestFotogr.make_empty_file("B.jpg")

        r = fotogr.search_for_keywords([TMPDIR], ["testcase"], [], [], True)
        self.assertEqual(r, ['/tmp/test-fotogr/a.jpg',
                             '/tmp/test-fotogr/b.jpg',
                             '/tmp/test-fotogr/A.jpg',
                             '/tmp/test-fotogr/B.jpg'])

        r = fotogr.search_for_keywords([TMPDIR], ["testcase"], [], [], False)
        self.assertEqual(r, ['/tmp/test-fotogr/a.jpg',
                             '/tmp/test-fotogr/b.jpg'])

        r = fotogr.search_for_keywords([TMPDIR], ["TestCase"], [], [], False)
        self.assertEqual(r, ['/tmp/test-fotogr/A.jpg',
                             '/tmp/test-fotogr/B.jpg'])


if __name__ == '__main__':
    unittest.main()

