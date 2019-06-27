#!/usr/bin/env python3

# Search books by author and, optionally, date (looking for recent books).
# Copyright 2019 by Akkana Peck, share and enjoy under the GPLv2 or later.

# Uses the Open Library API, https://openlibrary.org/
# but the database is not very up to date and is likely to be
# missing recent books, making this not particularly useful.

# Perhaps better is the worldcat API, though it requires signing up for a key.
# http://web.archive.org/web/20100616012651/http://worldcat.org/devnet/wiki/BasicAPIDetails
# But the WorldCat search API implies that you have to be a library
# to get an API key:
# https://www.oclc.org/developer/develop/web-services/worldcat-search-api.en.html
#
# Or maybe scrape the Library of Congress search pages;
# the LOC has APIs for seemingly everything *except* books,
# Typical LOC search page URL by author:
# https://catalog.loc.gov/vwebv/search?searchArg=connie+willis&searchCode=GKEY%5E*&searchType=1&limitTo=none&fromYear=&toYear=&limitTo=LOCA%3Dall&limitTo=PLAC%3Dall&limitTo=TYPE%3Dam&limitTo=LANG%3DENG&recCount=100&filter=Y
# They also have DMARC requests but they're only free up to 2013,
# anything more recent requires buying a license for DMARC downloads
# for something like $7k.

import requests
import json
import argparse
import sys
from pprint import pprint

def books_by_author(authorname):
    r = requests.get('http://openlibrary.org/search.json?author='
                     + '+'.join(authorname.split()))
    if r.status_code != 200:
        return None

    return json.loads(r.text)

class Book:
    def __init__(self, bookdict):
        if 'title' not in bookdict:
            raise RuntimeError('No title')

        if 'publish_year' not in bookdict:
            raise RuntimeError('%s has no publish year' % bookdict['title'])

        self.authors = bookdict['author_name']   # list of strings
        self.title = bookdict['title']           # string
        self.year = bookdict['publish_year'][0]  # int

        # Some books don't have languages listed.
        # If not, assume they're English.
        if 'language' in bookdict:
            self.languages = bookdict['language']    # list of strings
        else:
            self.languages = ['??']

    def __repr__(self):
        s = '"%s" (%s) %s' % (self.title,
                              ', '.join(self.authors),
                              self.year)

        if self.languages[0] == '??':
            s += " (language unknown)"

        return s

    def in_english(self):
        for lang in self.languages:
            if lang.startswith('eng'):
                return True
            if lang == '??':
                return True
        return False

    @staticmethod
    def by_year_key(book):
        return str(book.year) + str(book.title)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', action="store", dest="year", type=int,
                        help='year: Show only books from this year or later')
    parser.add_argument('authors', nargs='+', help="Authors")
    args = parser.parse_args(sys.argv[1:])
    print(args)

    for author in args.authors:
        bookdicts = books_by_author(author)
        if not bookdicts:
            print("==== No books by", author)
            continue

        print("====", author)

        books = []
        for bdict in bookdicts['docs']:
            try:
                books.append(Book(bdict))
            except RuntimeError as e:
                print(e)
                continue
            # except Exception as e:
            #     print("Unknown exception", e)
            #     pprint(bdict)
            #     continue

        # Sort to put most recent first
        books.sort(key=Book.by_year_key, reverse=True)

        for book in books:
            if not args.year or book.year >= args.year:
                print(book)
