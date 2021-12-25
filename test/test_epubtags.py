#!/usr/bin/env python3

# Tests for epubtag.py

# XXX A really thorough set of tests would include several books that use
# different formats, since there are so many variants of epub.
# Oh, well, this is a start.

import unittest

import os
import shutil

from ebooks import epubtag

class TestEpubTags(unittest.TestCase):
    # setUp() will be called for every test_*() function in the class.
    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_epubtags(self):
        """Test an actual book from Project Gutenberg"""

        bookdir = os.path.join(os.path.dirname(__file__), 'files')
        testsubdir = os.path.join(bookdir, 'temp')
        # Ensure the testsubdir is gone first. If the old cover image
        # is there, extract_images will extract the cover to
        # cover-1.jpg instead, which will fail the unit test.
        try:
            shutil.rmtree(testsubdir)
        except FileNotFoundError:
            pass
        os.mkdir(testsubdir)
        print("*** mkdir", testsubdir)

        bookfilename = os.path.join(testsubdir, 'hamlet.epub')
        shutil.copyfile(os.path.join(bookdir, 'hamlet.epub'), bookfilename)
        book = epubtag.EpubBook()
        book.open(bookfilename)
        book.parse_contents()

        self.assertEqual(book.get_title(), 'Hamlet')
        self.assertEqual(book.get_titles(), ['Hamlet'])
        self.assertEqual(book.get_tags(), ['Tragedy', 'Plays'])
        self.assertEqual(book.get_authors(), ['William Shakespeare'])
        self.assertEqual(book.info_string(), '''%s/hamlet.epub
Title: Hamlet
Author: William Shakespeare
Tags:
   Tragedy
   Plays''' % testsubdir)
        extracted_files = book.extract_images(outdir=testsubdir)
        self.assertEqual(extracted_files,
                         [os.path.join(testsubdir, 'cover.jpg')])
        st = os.stat(os.path.join(testsubdir, 'cover.jpg'))
        self.assertEqual(st.st_size, 19263)

        # Change tags
        book.add_tags(['soliloquies', 'Denmark'])
        self.assertEqual(sorted(book.get_tags()),
                         ['Denmark', 'Plays', 'Tragedy', 'soliloquies'])
        book.save_changes()

        shutil.rmtree(testsubdir)


    def test_langgrep(self):
        pass
