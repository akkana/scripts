#!/usr/bin/env python3

# Given places.sqlite3 from a Firefox profile,
# parse all the search terms that have been passed to Google.

import sqlite3
import shutil
import shlex
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import os, sys


def get_search_history(filename):
    newfilename = os.path.join("/tmp", os.path.basename(filename))
    if not os.path.exists(newfilename):
        print("Making a copy of", filename, "to", newfilename)
        shutil.copy(filename, newfilename)
    con = sqlite3.connect(newfilename)
    cur = con.cursor()
    cur.execute("SELECT url, last_visit_date FROM moz_places WHERE url like '%https://www.google.com/search?q=%'")

    # fetchedlist = [ cur.fetchall() ]   # list of (url, last_visit_date)
    fetchedlist = list(cur.fetchall())

    # Sort by date (second item), which is is unix time but in microseconds.
    fetchedlist.sort(key=lambda x: x[1] if x[1] else 0)
    # return [ pair[0] for pair in fetchedlist ]
    return fetchedlist


def find_search_terms(url, query_string=None):
    """Given either a url or a query_string, separate it into search terms.
    """
    if url:
        purl = urlparse(url)
        query = parse_qs(purl.query)
        query_string = query['q'][0]

    # print("query_string:", query_string)

    # query_string is something like 'python parse google url "query string"'
    # Use shlex to split but preserve double quotes (not single)
    lex = shlex.shlex(query_string)
    lex.quotes = '"'
    lex.whitespace_split = True
    lex.commenters = ''
    try:
        terms = list(lex)
    except ValueError as e:
        if str(e) == "No closing quotation":
            print(query_string, "quotation wasn't closed, adding a close-quote")
            # For unmatched double quotes, add a new double quote
            # at the end of the query string.
            return find_search_terms(None, query_string=query_string + '"')
        print("Exception:", e)

    return terms


if __name__ == '__main__':
    print(len(sys.argv))
    if len(sys.argv) < 2:
        print("Usage: %s /path/to/places.sqlite"
              % os.path.basename(sys.argv[0]))
        print("places.sqlite is probably in ~/.mozilla/firefox/profilename")
        sys.exit(1)

    pairs = get_search_history(sys.argv[1])
    for url, timestamp in pairs:
        # print("url, timestamp:", url, timestamp)
        terms = find_search_terms(url)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000000) \
                         .strftime("%Y-%m-%d %H:%M")
        else:
            # For a few of the db entries, the timestamp is null.
            # In most cases the search terms are null too.
            dt = ''
        print('%16s  %s' % (str(dt), str(terms)))





