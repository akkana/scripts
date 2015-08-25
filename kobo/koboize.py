#!/usr/bin/env python

# Convert regular epubs to kobo kepub.
# HTML manipulations from koboish,
# http://dsandrei.blogspot.fr/2012/07/koboish-ebooks.html

import sys, os
from bs4 import BeautifulSoup
import zipfile
import re

import epubtag

def convert_file(filename, destdir):
    if not filename.lower().endswith(".epub"):
        print filename, "Doesn't end with .epub"
        return

    if destdir:
        outbookname = os.path.join(destdir,
                                   os.path.basename(filename[:-5])
                                                    + ".kepub.epub")
    else:
        outbookname = filename[:-5] + ".kepub.epub"

    book = epubtag.EpubBook()
    book.open(filename)

    ozf = zipfile.ZipFile(outbookname, 'w')

    namelist = book.namelist()
    for name in namelist:
        # print "name:", name
        if name.endswith('.html') or name.endswith('.xhtml'):
            print "Converting", name
            fp = book.zip.open(name)
            soup = BeautifulSoup(fp)
            altertags(soup)
            fp.close()
            ozf.writestr(name, str(soup))
            print "altered", name
            of = open("/tmp/" + os.path.basename(name), "w")
            of.write(str(soup))
        else:
            ozf.writestr(name, book.zip.read(name))

    book.close()
    ozf.close()
    print "Converted", filename, "to", outbookname
    
def altertags(soup):
    counter = 1
    for tag in soup.body.find_all(re.compile("^(p|h[1-6])")):
         new_tag = soup.new_tag("span", id="kobo.%d.1" % counter)
         counter = counter + 1
         tag.wrap(new_tag)
         tag.unwrap()
         new_tag.wrap(tag)

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print "Usage: %s a.epub [b.epub c.epub ...] [destdir]" % \
            os.path.basename(sys.argv[0])
        sys.exit(1)

    files = sys.argv[1:]
    destdir = None

    # Is the last argument a directory?
    if os.path.isdir(files[-1]):
        destdir = files[-1]
        files = files[:-1]
        print "Koboizing to directory", destdir

    for arg in files:
        convert_file(arg, destdir)

