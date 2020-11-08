#!/usr/bin/env python3

# Tests for viewhtmlmail.py

import unittest

import os
import shutil
import hashlib
import time

import viewhtmlmail


def md5sum(filename):
    md5 = hashlib.md5()

    with open(filename, "rb") as f:
        while chunk := f.read(4096):
            md5.update(chunk)

    return md5.hexdigest()


class TestSampleMessage(unittest.TestCase):
    # setUp() will be called for every test_*() function in the class.
    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_sample_message(self):
        """Test a sample message to make sure that images, charsets etc.
           come through correctly.
        """

        tmpdir = os.path.abspath("test/files/tmp")
        print("tmpdir is", tmpdir)
        try:
            os.mkdir(tmpdir)
        except FileExistsError:
            pass

        viewhtmlmail.view_html_message("test/files/htmlmail.eml", tmpdir)

        print("Check to make sure the message window looks right")

        htmlfile = os.path.join(tmpdir, "viewhtml.html")
        self.assertTrue(os.path.exists(htmlfile))
        self.assertEqual(md5sum(htmlfile), "b15a4e42651073042ec01940a1eaed75")

        imgfile = os.path.join(tmpdir, "tuxnetwork.jpg")
        self.assertTrue(os.path.exists(imgfile))
        self.assertEqual(md5sum(imgfile), "a69eb0be3c99646e3e0f410861a70a60")

        # Remove the temp dir. But first, wait briefly for the
        # mail window to pop up.
        time.sleep(1)
        shutil.rmtree(tmpdir)

