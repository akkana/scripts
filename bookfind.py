#!/usr/bin/env python

# Search books by author and, optionally, date (looking for recent books).
# Copyright 2019 by Akkana Peck, share and enjoy under the GPLv2 or later.

# Currently uses either of two APIs:
# Python isbnlib or Goodreads.
# Goodreads requires an API key: create a file
# ~/.config/newreads/goodreads.keys
# containing one line:
# key YOUR_KEY_HERE
# isbnlib doesn't require a a key and so is the default.

######################################################################
# Notes on other possible APIs:
#
# Perhaps better is the worldcat API, though it requires signing up for a key.
# http://web.archive.org/web/20100616012651/http://worldcat.org/devnet/wiki/BasicAPIDetails
# But the WorldCat search API implies that you have to be a library
# to get an API key:
# https://www.oclc.org/developer/develop/web-services/worldcat-search-api.en.html
#
# https://isbndb.com/apidocs looks interesting, but isn't free.
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
# Don't request any method more often than once a second
##### end API notes ##################################################

import argparse
import time
import sys, os

class Book:
    monthnames = [ '?', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ]


    def __init__(self, ISBN, title, authorlist, description,
                 pub_year, pub_month, goodreads_id=0):
        self.ISBN13 = ISBN
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
        self.goodreads_id = int(goodreads_id)

        # Things that can be filled in later, which may or may not
        # be available from any given call:
        self.language = None


    # Books need to be sortable by publication date
    def __lt__(self, other):
        if self.pub_year < other.pub_year:
            return True
        if self.pub_year == other.pub_year and self.pub_month < other.pub_month:
            return True
        if self.pub_year == other.pub_year and \
           self.pub_month == other.pub_month:
            if self.ISBN13 and other.ISBN13:
                return self.ISBN13 < other.ISBN13
            if self.goodreads_id and other.goodreads_id:
                return self.goodreads_id < other.goodreads_id
        return False


    def __repr__(self):
        retstr = '%s, by %s' % (self.title, ','.join(self.authors))
        if self.pub_month:
            retstr += ' (%s %d)' % (Book.monthnames[self.pub_month],
                                    self.pub_year)
        elif self.pub_year:
            retstr += ' %d' % self.pub_year

        if self.ISBN13:
            retstr += ' (ISBN %s)' % self.ISBN13

        if self.goodreads_id:
            retstr += ' (Goodreads %d)' % self.goodreads_id

        return retstr


class ISBNlibAPI:
    def __init__(self):
        self.debug = False


    def book_by_ISBN(self, isbn):
        # print("Looking up ISBN", isbn)
        meta = isbnlib.meta(isbn)
        return Book(isbn, meta['Title'], meta['Authors'], '',
                    meta['Year'], 0)


    def book_by_id(self, bookid):
        return self.book_by_ISBN(bookid)


    def books_by_author(self, authorname):
        '''Find books by all authors matching the given name.
           authorname is a string like "Connie Willis")
           Order of names probably doesn't matter.
           Returns two lists: booklists, anthologies
           each of which consists of triples [year, month, title]
        '''
        booklist = []
        books = isbnlib.goom(authorname)
        for meta in books:
            booklist.append(Book(meta['ISBN-13'], meta['Title'],
                                 meta['Authors'], '',
                                 meta['Year'], 0))

        booklist.sort(reverse=True)
        return booklist, []


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

        self.debug = False


    def book_from_url(self, url):
        if self.debug:
            print("url", url)

        r = requests.get(url)
        if r.status_code != 200:
            if self.debug:
                raise RuntimeError("Bad status %d on %s" % (r.status_code, url))
            else:
                return None

        # print(r.text)
        soup = BeautifulSoup(r.text, 'lxml-xml')

        authorstag = soup.find('authors')
        authors = []
        for authortag in authorstag.findAll('author'):
            authors.append(authortag.find('name').text)
        title = soup.find('title').text

        desc = soup.find('description').text

        # The pages by goodreads ID seldom have pub year or month,
        # but the ISBN searches sometimes do. Doesn't hurt to try:
        try:
            pubyear = int(soup.find('original_publication_year').text)
        except:
            pubyear = 0
        try:
            pubmonth = int(soup.find('original_publication_month').text)
        except:
            pubmonth = 0

        try:
            gid = int(soup.find('id').text)
        except:
            gid = 0

        try:
            isbn13 = soup.find('isbn13').text
        except:
            isbn13 = 0

        return Book(isbn13, title, authors, desc, pubyear, pubmonth,
                    goodreads_id=gid)


    def book_by_ISBN(self, bookid):
        if self.debug:
            print("Looking up book by isbn", bookid)

        # The reviews page includes book description and language
        url = 'https://www.goodreads.com/book/isbn/%s?key=%s' \
            % (bookid, self.keys['key'])

        return self.book_from_url(url)


    def book_by_id(self, bookid):
        # The reviews page includes book description and language
        url = 'https://www.goodreads.com/book/show/%s.xml?key=%s' \
            % (bookid, self.keys['key'])

        return self.book_from_url(url)


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
        if self.debug:
            print("URL", url)

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
                if self.debug:
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

        # The Goodreads API has some sort of once-a-second limit,
        # but they're unclear exactly how that works,
        # which calls are limited. Just to be safe, it doesn't hurt
        # to wait a second between arguments.
        time.sleep(1)

        return booklist, anthologies


def lookup_books(args):
    for val in args.author_or_id:
        val = val.strip()

        # If the argument is all digits, it's presumably an ID,
        # either an ISBN13 or a Goodreads ID.
        if val.isdigit():
            if args.ISBN or len(val) == 13:
                book = api.book_by_ISBN(val)
                if not book:
                    print("No book with ISBN", val)
                    continue
            else:
                book = api.book_by_id(val)
                if not book:
                    print("No book with ID", val)
                    continue

            print(book)
            print(book.desc)

        else:
            booklist, anthologies = api.books_by_author(val)

            print("\n====", val)

            if args.anthologies:
                for book in anthologies:
                    if not args.year or book.pub_year >= args.year:
                        print(book)

            for book in booklist:
                if not args.year or book.pub_year >= args.year:
                    print(book)
                    if args.desc:
                        print(book.desc)
                        print()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', action="store_true", dest="anthologies",
                        help='Include anthologies that include this author')
    parser.add_argument('-y', action="store", dest="year", type=int,
                        help='year: Show only books from this year or later')
    parser.add_argument('-d', action="store_true", dest="desc",
                        help='description: show Goodreads descriptions')
    parser.add_argument('-G', action="store_true", dest="Goodreads",
                        help='Use the Goodreads API (requires API key)')
    parser.add_argument('-I', action="store_true", dest="ISBN",
                        help='Consider numbers as ISBN13 even if using the Goodreads API')
    parser.add_argument('-D', action="store_true", dest="debug",
                        help='Show debugging information, like URLs used')
    parser.add_argument('author_or_id', nargs='+',
                        help="Authors or Goodreads numerical IDs")

    args = parser.parse_args(sys.argv[1:])

    # Imports have to happen at the top level,
    # not in a function like lookup_books.
    if args.Goodreads:
        if args.debug:
            print("Using Goodreads API")
        import requests
        from bs4 import BeautifulSoup
        api = GoodreadsAPI()
    else:
        if args.debug:
            print("Using Python ISBNlib")
        import isbnlib
        api = ISBNlibAPI()

    if args.debug:
        api.debug = True

    try:
        lookup_books(args)

    except KeyboardInterrupt:
        print("Interrupt")
