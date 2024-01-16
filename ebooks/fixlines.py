#!/usr/bin/env python3

"""
Try to fix line lengths in epub converted using calibre's ebook-convert:
calibre makes every line in the PDF its own paragraph,
even if you use heuristics
ebook-convert infile.pdf outfile.epub --enable-heuristics
so all the text comes out looking double-spaced.
Sometimes it even splits lines in the middle of a word.
"""


import epubtag
from shutil import copyfile
from os.path import basename, join
from sys import argv


# lines read from the zip file are bytes, not string
PCLASS = b'<p class="calibre1">'
PCLASSLEN = len(PCLASS)


def fixlines(epubfile, maxlinelen=60):
    book = epubtag.EpubBook()
    book.open(epubfile)

    # Make a backup -- epubtag should do that before writing but might not
    backupfile = epubfile + ".bak"
    copyfile(epubfile, backupfile)

    # epubbase = basename(epubfile)
    # tmpfile = join("/tmp", epubbase)

    for cfilename in book.content_files():
        if not cfilename.lower().endswith(".html"):
            continue
        cfilebase = basename(cfilename)
        ctmpfile = join("/tmp", cfilebase)
        with book.zip.open(cfilename) as cfp:
            with open(ctmpfile, "wb") as tmpfp:
                in_paragraph = False
                for line in cfp:
                    sline = line.strip()
                    if (not sline.startswith(PCLASS) or
                        not sline.endswith(b'</p>')):
                        tmpfp.write(line)
                        continue
                    # It's a <p class="calibre1"> line.
                    if not in_paragraph:
                        tmpfp.write(b"<p>")
                        tmpfp.write(b'\n')
                        in_paragraph = True
                    # Get rid of the <p> baggage
                    line = line.strip()[PCLASSLEN:-4]

                    tmpfp.write(line)
                    tmpfp.write(b'\n')

                    # If the line is short, assume it should end a paragraph
                    linelen = len(line)
                    if linelen < maxlinelen:
                        tmpfp.write(b"</p>\n")
                        in_paragraph = False

                # Close the last paragraph
                if in_paragraph:
                    tmpfp.write(b"</p>\n")
                    in_paragraph = False

        book.replace_file(cfilename, ctmpfile)

    book.save_changes()


if __name__ == '__main__':
    for book in argv[1:]:
        fixlines(book)


