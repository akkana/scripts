#!/usr/bin/env python

# Turn tables in a Wikipedia page into CSV files

import urllib2
from bs4 import BeautifulSoup
import csv
import sys, os

def parse_table(inurl, outfile):
    # Read the Wikipedia URL:
    page = urllib2.urlopen(inurl)

    soup = BeautifulSoup(page, "lxml")

    writer = csv.writer(outfile)

    all_tables = soup.find_all('table', class_='wikitable sortable')

    last_headers = None

    for table in all_tables:
        rows = table.findAll("tr")
        for i, row in enumerate(rows):
            cells = [ c.text.replace('\n', ' ').encode(sys.getdefaultencoding(),
                                                       'backslashreplace')
                      for c in row.findAll(['td', 'th']) ]
            if i == 0:
                if cells != last_headers:
                    last_headers = cells
                    writer.writerow(cells)
                continue

            # print '\t'.join(cells)
            writer.writerow(cells)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        inurl = sys.argv[1]
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        inurl = sys.argv[1]
        outfile = open(sys.argv[2], "w")
    else:
        print "Usage: %s inurl [outfile.csv]" % os.path.basename(sys.argv[0])
        print "If no outfile is specified, will write to standard output."
        sys.exit(1)

    parse_table(inurl, outfile)
    if outfile != sys.stdout:
        outfile.close()
        print "Wrote", sys.argv[2]
