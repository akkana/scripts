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
#
# Other sites that could be scrapd:
# https://www.bookseriesinorder.com/connie-willis/
# https://www.fictiondb.com/search/searchresults.htm?srchtxt=robin+sloan
#
# The Goodreads API https://www.goodreads.com/api/
# might be able to do it, but their documentation is so bad that you have
# to sign up for an API key and try stuff even to see what they offer.
# Don't request any method more often than once a second

import requests
# import json
from bs4 import BeautifulSoup
import argparse
import sys, os

class GoodreadsAPI:
    def __init__(self):
        # Read keys
        self.keys = {}
        keyfilename = "~/.config/newreads/goodreads.keys"
        with open(os.path.expanduser(keyfilename)) as keyfile:
            for line in keyfile:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                self.keys[parts[0].strip()] = parts[1].strip()

        if 'key' not in self.keys:
            raise(RuntimeError("No key found in " + keyfile))

        # The "secret" goodreads key is for writing back to their database.
        # This app doesn't do that anyway, but just in case it ever might:
        # if 'secret' not in self.keys:
        #     print("API key is there, but won't be able to write")


    def books_by_author(self, authorname):
        '''Find books by all authors matching the given name.
           authorname is a string like "Connie Willis")
           Order of names probably doesn't matter.
           Returns two lists: booklists, anthologies
           each of which consists of triples [year, month, title]
        '''

        # Url encode, either with %20 or with +, don't care.
        authorname = requests.utils.requote_uri(authorname)

        url = "https://www.goodreads.com/api/author_url/%s?key=%s" \
            % (authorname, self.keys['key'])

        # print("URL", url)
        r = requests.get(url)
        if r.status_code != 200:
            raise RuntimeError("Bad status %d on %s" % (r.status_code, url))

        # This returns XML that includes <author id="NNNNN">
        soup = BeautifulSoup(r.text, 'lxml')
        author_tags = soup.findAll('author')
        if not author_tags:
            return None

        booklists = []

        for authortag in author_tags:
            author_id = authortag.get('id')
            author_name = authortag.get('name')
            if not author_id:
                raise RuntimeError("No id in author tag:", author)

            booklist = []
            anthologies = []

            # Now page through the author's books
            page = 1
            while True:
                url = "https://www.goodreads.com/author/list/%s" \
                      "?format=xml&key=%s&page=%d" \
                      % (author_id, self.keys['key'], page)

                print('%d... ' % page, end='', file=sys.stderr)
                sys.stderr.flush()
                r = requests.get(url)
                if r.status_code != 200:

                    raise RuntimeError("Bad status %d on %s" % (r.status_code,
                                                                url))

                soup = BeautifulSoup(r.text, 'lxml')
                bookstag = soup.find('books')
                if not bookstag:
                    print("Eek, author", author_id, "doesn't have any books")
                    break
                start = bookstag.get('start')
                end   = bookstag.get('end')
                total = bookstag.get('total')
                # print("\npage %s (%s-%s of %s)" % (page, start, end, total))

                for booktag in bookstag.findAll('book'):
                    title = booktag.find('title').text
                    book_id = booktag.get('id')
                    publication_year = booktag.find('publication_year').text
                    try:
                        publication_year = int(publication_year)
                    except:
                        publication_year = 1099
                    publication_month = booktag.find('publication_month').text
                    try:
                        publication_month = int(publication_month)
                    except:
                        publication_month = 0

                    # print("%s (%s %s)" % (title,
                    #                       publication_month,
                    #                       publication_year))

                    # See if this is really a book authored by this author.
                    # Goodreads inexplicably gives huge long lists that
                    # include lots of books this author had nothing to do with.
                    # Unfortunately, we can't just quit at that point;
                    # valid books aren't necessarily listed before bogus books.
                    bookauthors = booktag.findAll('author')
                    isauthor = False
                    for auth in bookauthors:
                        thisid = auth.find('id').text
                        if thisid == author_id:
                            # It's valid, the author really wrote it.
                            # Add it to the book list.
                            isauthor = True
                            booklist.append((publication_year,
                                             publication_month,
                                             title, book_id))
                            break
                    if not isauthor:
                        anthologies.append((publication_year,
                                            publication_month,
                                            title, book_id))

                if int(end) >= int(total):
                    booklist.sort(reverse=True)
                    anthologies.sort(reverse=True)
                    print()
                    return booklist, anthologies

                page += 1

            # Should never get here, but you never know.
            print("Somehow ended loop without finishing the list")
            print("Total was %s, this page had %d books, %s - %s"
                  % (total, len(bookstag), start, end))
            booklist.sort(reverse=True)
            anthologies.sort(reverse=True)
            print()
            return booklist, anthologies


monthnames = [ '?', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ]


def bookline(book):
    if not book[1]:
        return '%s (%d)' % (book[2], book[0])
    return '%s (%s %d) (Goodreads %s)' % (book[2], monthnames[book[1]],
                                          book[0],
                                          book[3])

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', action="store_true", dest="anthologies",
                        help='Include anthologies that include this author')
    parser.add_argument('-y', action="store", dest="year", type=int,
                        help='year: Show only books from this year or later')
    parser.add_argument('authors', nargs='+', help="Authors")
    args = parser.parse_args(sys.argv[1:])

    api = GoodreadsAPI()

    for author in args.authors:
        booklist, anthologies = api.books_by_author(author)

        print("\n====", author)

        if args.anthologies:
            for book in anthologies:
                if not args.year or book[0] >= args.year:
                    print(bookline(book))

        for book in booklist:
            if not args.year or book[0] >= args.year:
                print(bookline(book))
