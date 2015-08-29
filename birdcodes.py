#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Get bird codes from http://www.pwrc.usgs.gov/BBL/MANUAL/speclist.cfm
# which also points to
# http://www.pwrc.usgs.gov/BBL/xml/Mapped_XML_files/speciestable.xml
# which is smaller, but has less data: no scientific names,
# no capitalization info because it's all caps.

import sys
import re
import urllib2
from bs4 import BeautifulSoup

class BirdCodes:
    def __init__(self):
        self.bird_dict = {}

    def print_bird(self, code):
        print "%s :: %s :: %s" % (code, self.bird_dict[code]['name'],
                                  self.bird_dict[code]['sci_name'])

    def print_all(self):
        keys = self.bird_dict.keys()
        keys.sort()
        for code in keys:
            print "%s :: %s :: %s" % (code, self.bird_dict[code]['name'],
                                      self.bird_dict[code]['sci_name'])

    def parse_html_table(self):
        '''Return a dictionary of { code: { name: "", sci_name: "" } }
           parsed from the HTML website.
        '''
        page = urllib2.urlopen('http://www.pwrc.usgs.gov/BBL/MANUAL/speclist.cfm')
        birdpage = page.read()
        page.close()
        self.soup = BeautifulSoup(birdpage)

        for tr in self.soup.findAll('tr'):
            tds = tr.findAll('td')
            if not tds:
                # Probably just the header row. Skip it.
                continue

            try:
                code = tds[1].findAll(text=True)[0].strip() # if tds[1] else ''
                name = tds[2].findAll(text=True)[0].strip()
                sci = tds[5].findAll(text=True)[0].strip()
                self.bird_dict[code] = { 'name': name, 'sci_name': sci }
            except:
                print "Eek!", tr

    def parse_xml(self):
        '''Return a dictionary of code: [ common_name, scientific_name ]
           parsed from the XML web page.
        '''
        page = urllib2.urlopen('http://www.pwrc.usgs.gov/BBL/xml/Mapped_XML_files/speciestable.xml')
        birdxml = page.read()
        page.close()
        self.soup = BeautifulSoup(birdxml)
        for data in self.soup.findAll('speciesdata'):
            code = data.find('alphacode').get_text()
            name = data.find('commonname').get_text()
            # In the XML file names are all uppercase. Convert to initial caps:
            name = name[0] + name[1:].lower()
            # The XML file doesn't have scientific names

            self.bird_dict[code] = { 'name': name, 'sci_name': '' }

if __name__ == '__main__':
    codes = sys.argv[1:]

    bc = BirdCodes()

    if codes and codes[0] == '-l':
        longform = True
        codes = codes[1:]
    else:
        longform = False

    if longform:
        bc.parse_html_table()
    else:
        bc.parse_xml()

    if not codes:
        bc.print_all()

    for code in codes:
        bc.print_bird(code)


