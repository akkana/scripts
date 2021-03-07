#!/usr/bin/env python3

# Convert Word files, either doc or docx, to HTML
# using python-mammoth for .docx to HTML
# and unoconv (if available) or wvHtml (otherwise) for .doc.

from __future__ import print_function

import sys
import os.path
import subprocess

import mammoth
from bs4 import BeautifulSoup
import prettysoup


def docx2html(infile):
    with open(infile, 'rb') as fp:
        mammout = mammoth.convert_to_html(fp)
    for m in mammout.messages:
        print("Mammoth %s: %s" % (m.type, m.message))

    return prettyprint_html(mammout.value, infile)


def docx2htmlfile(infile, outfile):
    html = docx2html(infile)

    if outfile == "--":
        print(html)
    else:
        with open(outfile, "w") as fp:
            print(html, file=fp)


def prettyprint_html(inhtml, filename=''):
    '''Prettyprint some HTML, which is assumed not to
       have <html>, <head>, <body>..
    '''
    soup = BeautifulSoup(inhtml, "lxml")

    # Try to get a title:
    if soup.head and soup.head.title:
        title = soup.head.title.text
    elif soup.h1:
        title = soup.h1.text
    else:
        print("filename is", filename)
        title = os.path.splitext(filename)[0]
    if title:
        title = '<title>' + title + '</title>'

    # Failed attempts to add meta charset via BS:
    # # Add <meta charset="UTF-8"> at beginning of <head>
    # head = soup.head
    # if not head:
    #     print("There's no head")
    #     head = soup.new_tag('head')
    #     soup.body.insert_before(head)
    # metatag = soup.new_tag('meta')
    # metatag.attrs['http-equiv'] = 'Content-Type'
    # metatag.attrs['content'] = 'text/html; charset=utf-8"'
    # # soup.head.append(metatag)
    # soup.head.insert(0, metatag)

    # BS adds <body> but not <head>
    header = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
</head>
''' % title
    footer = '</html>'

    return header + prettysoup.prettyprint(soup.body) + footer
    # return soup.prettify().encode("utf-8")

def html2html(infile, outfile):
    with open(infile) as infp:
        pphtml = prettyprint_html(infp.read(), infile)
        with open(outfile, "w") as outfp:
            outfp.write(pphtml)

def doc2html(infile, outfile):
    base, ext = os.path.splitext(infile)
    docxfile = base + ".docx"
    try:
        # Unoconv always fails the first time with default args:
        # it takes too long for its server to start up,
        # so it needs a longer timeout. See:
        # https://github.com/dagwieers/unoconv/issues/415
        rv = subprocess.call(["unoconv", "-f", "docx", "-T", "10",
                              "-o", docxfile, infile])
    except OSError:
        rv = 1
    if not rv:
        docx2htmfilel(docxfile, outfile)
        print("removing", docxfile)
        os.unlink(docxfile)
        return

    # unoconv failed. Try wvHtml.
    print("Warning: %s: unoconv returned %d. Trying wvHtml" % (infile, rv))
    try:
        rv = subprocess.call(["wvHtml", infile, outfile])
    except OSError:
        rv = 1
    if not rv:
        return

    print("Couldn't convert %s with either unoconv or wvHtml. Aborting."
          % infile)
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3 \
       or sys.argv[1] == "-h" or sys.argv[1] == "--help":
        print("Usage: %s infile.docx [outfile.html]"
              % os.path.basename(sys.argv[0]))
        sys.exit(1)
    infile = sys.argv[1]
    base, ext = os.path.splitext(infile)
    if len(sys.argv) == 3:
        outfile = sys.argv[2]
    elif ext == ".html":
        outfile = base + "-pp.html"
    else:
        outfile = base + ".html"

    if ext.lower() == ".doc":
        doc2html(infile, outfile)

    elif ext.lower() == ".html":
        # If it's already HTML, just prettyprint it.
        # It's a handy way of doing so since otherwise there's no
        # command-line prettyprinter.
        html2html(infile, outfile)

    else:
        docx2htmlfile(infile, outfile)

    print("Wrote to %s" % outfile)
