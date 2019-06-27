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

class Book:
    monthnames = [ '?', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ]


    def __init__(self, id, title, authorlist, description,
                 pub_year, pub_month):
        self.id = int(id)
        self.title = title
        self.authors = authorlist
        self.desc = description
        try:
            self.pub_year = int(pub_year)
        except:
            self.pub_year = 0
        try:
            self.pub_month = int(pub_month)
        except:
            self.pub_month = 0

        # Things that can be filled in later, which may or may not
        # be available:
        self.language = None
        self.isbn = None
        self.isbn13 = None


    # Books need to be sortable by publication date
    def __lt__(self, other):
        if self.pub_year < other.pub_year:
            return True
        if self.pub_year == other.pub_year and self.pub_month < other.pub_month:
            return True
        if self.pub_year == other.pub_year and \
           self.pub_month == other.pub_month:
            return self.id < other.id
        return False


    def __repr__(self):
        if self.pub_month:
            return '%s (%s %d) (Goodreads %s)'\
                % (self.title,
                   Book.monthnames[self.pub_month],
                   self.pub_year, self.id)
        return '%s (%d) (Goodreads %s)' \
            % (self.title, self.pub_year, self.id)


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


    def book_description(self, bookid):
        # The reviews page includes book description and language
        url = 'https://www.goodreads.com/book/show/%d.xml?key=%s' \
            % (bookid, self.keys['key'])
        print("url", url)

        r = requests.get(url)
        if r.status_code != 200:
            raise RuntimeError("Bad status %d on %s" % (r.status_code, url))

        # print(r.text)
        soup = BeautifulSoup(r.text, 'lxml-xml')

        authorstag = soup.find('authors')
        authors = []
        for authortag in authorstag.findAll('author'):
            authors.append(authortag.find('name').text)

        title = soup.find('title').text

        desc = soup.find('description')
        # print("description tag:", desc)
        desc = desc.text

        return title + ", by " + ','.join(authors) + '\n' + desc


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
        soup = BeautifulSoup(r.text, 'lxml-xml')
        author_tags = soup.findAll('author')
        if not author_tags:
            print("No authors found matching '%s'" % authorname)
            return None, None

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
                print("url", url)

                print('%d... ' % page, end='', file=sys.stderr)
                sys.stderr.flush()
                r = requests.get(url)
                if r.status_code != 200:

                    raise RuntimeError("Bad status %d on %s" % (r.status_code,
                                                                url))

                soup = BeautifulSoup(r.text, 'lxml-xml')
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

                    book_id = booktag.find('id').text

                    # isbn isn't reliably available from author search pages
                    # isbn = booktag.find('isbn').text
                    # isbn13 = booktag.find('isbn13').text

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

                    desc = booktag.find('description')
                    if desc:
                        desc = desc.text
                    else:
                        desc = ''

                    # print("%s (%s %s)" % (title,
                    #                       publication_month,
                    #                       publication_year))

                    # See if this is really a book authored by this author.
                    # Goodreads inexplicably gives huge long lists that
                    # include lots of books this author had nothing to do with.
                    # Unfortunately, we can't just quit at that point;
                    # valid books aren't necessarily listed before bogus books.
                    bookauthors = booktag.findAll('author')
                    authorlist = []
                    isauthor = False
                    for auth in bookauthors:
                        authorlist.append(auth.find('name').text)
                        thisid = auth.find('id').text
                        if thisid == author_id:
                            # It's valid, the author really wrote it.
                            # Add it to the book list.
                            isauthor = True

                    if isauthor:
                        booklist.append(Book(book_id, title,
                                             authorlist,
                                             desc,
                                             publication_year,
                                             publication_month))
                    else:
                        anthologies.append(Book(book_id, title,
                                             authorlist,
                                             desc,
                                             publication_year,
                                             publication_month))

                if int(end) >= int(total):
                    break

                page += 1

        booklist.sort(reverse=True)
        anthologies.sort(reverse=True)
        return booklist, anthologies


if __name__ == '__main__':

    # book2019 = Book(1234, 'Book 2019', ['a b'], '', 2019, 0)
    # book2019_2 = Book(1234, 'Book 2 2019', ['a b'], '', 2019, 2)
    # book2017 = Book(1234, 'Book 2017', ['a b'], '', 2017, 5)
    # book2014 = Book(1234, 'Book 2014', ['a b'], '', 2014, 9)
    # books = [ book2017, book2019, book2014, book2019_2 ]
    # print(sorted(books))
    # sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', action="store_true", dest="anthologies",
                        help='Include anthologies that include this author')
    parser.add_argument('-y', action="store", dest="year", type=int,
                        help='year: Show only books from this year or later')
    parser.add_argument('-d', action="store", dest="desc", type=int,
                        help='description: show Goodreads description for this book')
    parser.add_argument('author', nargs='*', help="Authors")
    args = parser.parse_args(sys.argv[1:])

    api = GoodreadsAPI()

    if args.desc:
        print(api.book_description(args.desc))
        sys.exit(0)

    for author in args.author:
        author = author.strip()

        booklist, anthologies = api.books_by_author(author)

        print("\n====", author)

        if args.anthologies:
            for book in anthologies:
                if not args.year or book.pub_year >= args.year:
                    print(book)

        for book in booklist:
            if not args.year or book.pub_year >= args.year:
                print(book)
