#! /usr/bin/env python3

# Utilities viewing and modifying the tags inside epub books.
#
# Copyright 2015,2018,2019 by Akkana Peck.
# Share and enjoy under the GPL v2 or later.

from __future__ import print_function

import os
import sys
import zipfile
import xml.dom.minidom


class EpubBook:
    # class constants:
    subjectTag = 'dc:subject'
    image_exts = [".jpg", ".jpeg", ".gif", ".png", ".svg", ".pdf"]

    def __init__(self, filename=None):
        self.zip = None
        self.dom = None
        self.contentfile = None
        if filename:
            self.open(filename)
        else:
            self.filename = None

    def open(self, filename):
        """Open an epub file and set up handles to the zip archive
           and the DOM for the OPF file with all the metadata.
        """
        if not zipfile.is_zipfile(filename):
            raise RuntimeError(filename + " isn't an epub file (not zipped)")

        self.filename = filename
        self.zip = zipfile.ZipFile(filename)
        self.replace_files = {}

    def namelist(self):
        return self.zip.namelist()

    def parse_contents(self):
        # Parse the OPF file into self.dom.
        if not self.zip:
            raise RuntimeError('Epub book not opened')

        for f in self.zip.namelist():
            if os.path.basename(f).endswith('.opf'):
                if self.contentfile:
                    raise RuntimeError("Multiple opf files in %s"
                                       % self.filename)
                self.contentfile = f
                content = self.zip.open(f)
                break
        if not content:
            raise RuntimeError('No .opf file in %s' % self.filename)
            return

        # Now content is a file handle on the content.opf XML file
        try:
            self.dom = xml.dom.minidom.parse(content)
        except IOError as e:
            raise IOError(self.filename + ': ' + str(e))
        except xml.parsers.expat.ExpatError as e:
            print("Can't parse %s: Expat error, %s" % (self.filename, str(e)),
                  file=sys.stderr)

        content.close()

    def close(self):
        self.zip.close()
        self.filename = None
        self.zip = None
        self.dom = None

    def get_matches(self, elname, delete_tags=False):
        """Internal function:
           find matching tags in the OPF DOM (e.g. 'dc:title').
           If delete_tags is true, all such tags will be deleted
           along with any children.
        """
        if not self.dom:
            self.parse_contents()

        elements = self.dom.getElementsByTagName(elname)
        parent = None
        matches = []
        for el in elements:
            # Obviously there should be more error checking here
            if not parent:
                parent = el.parentNode
            else:
                assert parent == el.parentNode

            if delete_tags:
                if el.childNodes:
                    print("Deleting:", el.childNodes[0].wholeText)
                else:
                    print("Deleting empty", elname, "tag")
                el.parentNode.removeChild(el)

            elif el.childNodes:
                # el.childNodes[0].wholeText is the unicode.
                # Turn it into UTF-8 before returning.
                # Uncomment the next line and run on micromegas.epub
                # to test a weird thing: it happens if you run
                # epubtag.py micromegas.epub | cat
                # but not if you just run
                # epubtag.py micromegas.epub
                # See http://stackoverflow.com/questions/492483/setting-the-correct-encoding-when-piping-stdout-in-python
                # matches.append(el.childNodes[0].wholeText)

                # In Python2, el.childNodes[0].wholeText is type unicode,
                # and has to be encoded into utf-8 to do anything useful
                # with it, like print it.
                # In Python3, el.childNodes[0].wholeText is type str,
                # and if you call encode on it it turns into bytes
                # which you can't do anything useful with. Argh.
                wholetext = el.childNodes[0].wholeText
                if type(wholetext) is not str:
                    wholetext = wholetext.encode('utf-8', 'backslashreplace')
                matches.append(wholetext)
            else:
                print("Empty", elname, "tag")

        return matches, elements, parent

    def get_titles(self):
        """Get the title for this work. Returns a list since it's
           possible for an epub to have more than one title.
        """
        titles, elements, parent = self.get_matches('dc:title')
        return titles

    def get_title(self):
        """Get the first (perhaps only) title.
        """
        return self.get_titles()[0]

    def set_title(self, newtitle):
        titles, elements, parent = self.get_matches('dc:title')
        for el in elements:
            if el.firstChild.nodeType == el.TEXT_NODE:
                el.firstChild.replaceWholeText(newtitle)
            else:
                print("Error: dc:title contains something other than text")

    def get_authors(self):
        """Get the list of authors (perhaps only one of them).
        """
        authors, elements, parent = self.get_matches('dc:creator')
        return authors

    def get_tags(self):
        """Get all tags in this epub book.
        """
        # Tags are inside <metadata> and look like this:
        # <metadata>
        #   <dc:subject>Presidents -- United States -- Biography</dc:subject>
        # Author (dc:creator) and Title (dc:title) are stored similarly.

        tags, elements, parent = self.get_matches(self.subjectTag)
        return tags

    def info_string(self, brief=False):
        """Return an info string describing this book, suitable for printing.
        """
        outstr = self.filename + '\n'

        # grab the title and author
        titles = self.get_titles()
        if brief:
            outstr += ', '.join(titles) + " | "
        else:
            for t in titles:
                outstr += "Title: " + t + "\n"

        authors = self.get_authors()
        if brief:
            outstr += ', '.join(authors) + ' | '
        else:
            if len(authors) > 1:
                outstr += "Authors: "
            else:
                outstr += "Author: "
            outstr += ', '.join(authors) + "\n"

        tags = self.get_tags()
        if brief:
            outstr += ', '.join(tags)
        else:
            if tags:
                outstr += "Tags:"
                for tag in tags:
                    outstr += '\n   ' + tag

        return outstr

    def delete_tags(self):
        """Delete all tags in the book.
        """
        tags, elements, parent = self.get_matches(self.subjectTag, True)

    def add_tags(self, new_tag_list):
        """Add the given tags to any tags the epub already has.
        """
        tags, elements, parent = self.get_matches(self.subjectTag)

        lowertags = [s.lower() for s in tags]

        # If we didn't see a dc:subject, we still need a parent,
        # the <metadata> tag.
        if not parent:
            print("Warning: didn't see any subject tags previously")
            parent = self.dom.getElementsByTagName("metadata")[0]

            # If there's no metadata tag, maybe we should add one,
            # but it might be better to throw an error.
            if not parent:
                raise RuntimeError("No metadata tag! Bailing.")

        # Add the new subject tags after the last one.
        if elements:
            last_tag_el = elements[-1]
        else:
            last_tag_el = None

        for new_tag in new_tag_list:
            # Don't add duplicate tags (case-insensitive).
            new_tag_lower = new_tag.lower()
            if new_tag_lower in lowertags:
                print("Skipping duplicate tag", new_tag)
                continue

            # Make the new node:
            # newnode = tag.cloneNode(False)
            newnode = self.dom.createElement(self.subjectTag)

            # Suddenly all the parsers insist on seeing this element
            # in the new dc: tags, which didn't seem to be needed before.
            newnode.setAttribute("xmlns:dc",
                                 "http://purl.org/dc/elements/1.1/")

            # Make a text node inside it:
            textnode = self.dom.createTextNode(new_tag)
            newnode.appendChild(textnode)

            # Also add a newline after each new node
            textnode = self.dom.createTextNode('\n')

            # Append newnode after the last tag node we saw:
            if last_tag_el and last_tag_el.nextSibling:
                parent.insertBefore(textnode, last_tag_el.nextSibling)
                parent.insertBefore(newnode, textnode)
            # If we didn't see a tag, or the tag was the last child
            # of its parent, we have to do it this way:
            else:
                parent.appendChild(newnode)
                parent.appendChild(textnode)

            print("Adding:", new_tag)

    def replace_file(self, oldfilename, newfile):
        """When we save_changes, replace the contents of oldfilename
           (without changing its filename) with the contents of newfile,
           a filename on the local filesystem.
        """
        self.replace_files[oldfilename] = newfile

    def save_changes(self):
        """Overwrite the old file with any changes that have been
           made to the epub's tags. The old file will be backed
           up in filename.bak.
        """
        # Open a new zip file to write to, and copy everything
        # but change the content.opf (or whatever.opf) to the new one:
        new_epub_file = self.filename + '.tmp'
        ozf = zipfile.ZipFile(new_epub_file, 'w')
        for info in self.zip.infolist():
            if info.filename in self.replace_files:
                fp = open(self.replace_files[info.filename])
                ozf.writestr(info, fp.read())
                fp.close()
            elif info.filename == "mimetype":
                # The mimetype file must be written uncompressed.
                ozf.writestr(info, self.zip.read(info.filename),
                             zipfile.ZIP_STORED)
            elif info.filename.endswith('.opf'):
                # dom.toprettyprintxml() returns unicode, which
                # zipfile.writestr() can't write. If you pass in
                # encoding= then it works ... but minidom gives us
                # no way to find out the encoding of the XML file
                # we just parsed! So the best we can do is force
                # it to UTF-8, barring re-opening the file and
                # parsing the first line manually. So crazy!
                # Even worse, if there's a nonascii character in the metadata,
                # in Python 2 self.dom.toxml(encoding='utf-8') will die with
                # "UnicodeDecodeError: 'ascii' codec can't decode byte"
                # apparently ignoring the encoding passed in.
                # It's probably possible to fix this -- but in Python 3
                # it doesn't happen, so let's just catch it and warn.
                try:
                    ozf.writestr(info, self.dom.toxml(encoding='utf-8'))
                except UnicodeDecodeError as e:
                    print("""
******
Python 2 minidom has trouble encoding non-ASCII characters")
"You'd be better off using Python 3 for this book
******
""")
                    raise(e)

                # toprettyxml keeps the old whitespace and also adds
                # additional new whitespace ... including trailing
                # whitespace on every line. Not best.
                # ozf.writestr(info, self.dom.toprettyxml(encoding=encoding,
                #                                         indent=" ",
                #                                         newl=''))
                # This also works:
                # ozf.writestr(info,
                #              self.dom.toprettyxml().encode(encoding,
                #                                      'xmlcharrefreplace'))
            else:
                # For every other file, just copy directly.
                try:
                    ozf.writestr(info, self.zip.read(info.filename))
                except OSError as e:
                    print("Exception on filename", info.filename)
                    print(e)

        ozf.close()

        # Now we have the new file in new_epub_file, old in filename.
        # Rename appropriately:
        bakfile = self.filename + ".bak"
        os.rename(self.filename, bakfile)
        os.rename(new_epub_file, self.filename)
        print("Wrote", self.filename)
        os.remove(bakfile)

    def extract_cover_image(self, outdir=''):
        """Extract just an image named cover.*.
           Return (newfilename, filename_in_zip_archive)
           or (None, None) if it can't find anything.
        """
        """
        Notes on covers: the epub format doesn't actually specify how to make
        a cover, so apparently there are all sorts of different conventions.

        Gutenberg books tend to have
        <metadata>
            <meta content="item8" name="cover"/>
        </metadata>
        <manifest>
            <item href="cover.jpg" id="item8" media-type="image/jpeg"/>
        </manifest>
        <guide>
            <reference href="cover.jpg" title="Cover Image" type="cover"/>
        </guide>

        A book converted from HTML with early Calibre has:
        <metadata>
            <meta content="cover" name="cover"/>
        </metadata>
        <manifest>
            <item href="Images/cover_image.jpg"
                  id="cover" media-type="image/jpeg"/>
        </manifest>
        <guide>
            <reference href="Text/titlepage.xhtml"
                       title="Title Page" type="cover"/>
        </guide>

        A StoryBundle book has:
        <metadata>
            <meta name="cover" content="cover"/>
        </metadata>
        <manifest>
            <item href="cover.jpeg" id="cover" media-type="image/jpeg"/>
        </manifest>
        <guide>
            <reference href="titlepage.xhtml" title="Cover" type="cover"/>
        </guide>

        A random commercial book has:
        <metadata>
            <meta content="coverimg" name="cover"/>
            <meta content="cover-image" name="cover"/>
        </metadata>
        <manifest>
            <item href="OEBPS/images/bookname_epub3_001_cvi.jpg"
                  id="coverimg" media-type="image/jpeg"
                  properties="cover-image"/>
        </manifest>
        <guide>
            <reference href="OEBPS/bookname_epub3_cvi_r1.xhtml"
                       title="Cover" type="cover"/>
        </guide>

        What O'Reilly says to have:
        <metadata>
            <meta name="cover" content="cover-image" />
        </metadata>
        <manifest>
            <item id="cover" href="cover.html"
                  media-type="application/xhtml+xml"/>
            <item id="cover-image" href="the_cover.jpg"
                  media-type="image/jpeg"/>
        </manifest>
        <guide>
            <reference href="cover.html" type="cover" title="Cover"/>
        </guide>

        What the MobileRead Wiki says to have:
        <metadata>
             <meta name="cover" content="cover-image"/>
        </metadata>
        <manifest>
             <item id="cover" href="the-cover-filename.xhtml"
                   media-type="application/xhtml+xml"/>
             <item id="cover-image" href="the_cover.jpg"
                   media-type="image/jpeg"/>
        </manifest>
        <guide>
            <reference type="cover" href="the-cover-filename.xhtml" />
        </guide>

        Practically, what to look for:
        1. <item id="cover-image" in <manifest>  # O'Reilly/MobileReads rec
        2. <item id="coverimg" in <manifest>     # Commercial
        3. <item id="cover" in <manifest>        # Early Calibre
        4. <reference type="cover" in <guide>    # Gutenberg
        What a mess!

        Some URLs suggesting best practices:
        https://www.safaribooksonline.com/blog/2009/11/20/best-practices-in-epub-cover-images/
        http://wiki.mobileread.com/wiki/Ebook_Covers
        """

        coverimg = None
        parent = self.dom.getElementsByTagName("manifest")[0]
        for item in parent.getElementsByTagName("item"):
            id = item.getAttribute("id").lower()
            if id.startswith("cover"):
                coverimg = item.getAttribute("href")
                base, ext = os.path.splitext(coverimg)
                if ext in self.image_exts:
                    break
                # If it doesn't end with an image type, we can't use it
                coverimg = None

        # If we didn't find one in the manifest, try looking in guide:
        if not coverimg:
            guide = self.dom.getElementsByTagName("guide")
            if guide:
                parent = guide[0]
                for item in parent.getElementsByTagName("reference"):
                    if item.getAttribute("type").lower() == "cover":
                        coverimg = item.getAttribute("href")
                        base, ext = os.path.splitext(coverimg)
                        if ext in self.image_exts:
                            break
                        # If it doesn't end with an image type, we can't use it
                        coverimg = None

        # If all else fails, go back to the manifest and look for
        # anything named cover.jpg. This is the only recourse for
        # many Project Gutenberg books.
        if not coverimg:
            parent = self.dom.getElementsByTagName("manifest")[0]
            for item in parent.getElementsByTagName("item"):
                href = item.getAttribute("href")
                base, ext = os.path.splitext(os.path.basename(href))
                if base.lower() == "cover":
                    coverimg = href

        if not coverimg:
            print("No cover image")
            return None, None

        infp = None
        base = os.path.basename(coverimg)

        # If we get here, we think we have the name of the cover image file.
        # Unfortunately, it's not necessarily a full path.
        # We may need to search for it in the zip.
        try:
            infp = self.zip.open(coverimg)
        except KeyError:
            for f in self.zip.namelist():
                if os.path.basename(f) == base:
                    infp = self.zip.open(f)
                    coverimg = f
        if not infp:
            print("Couldn't find", coverimg, "in zip archive")
            return None, None

        outfilename = os.path.join(outdir, base)
        outfp = open(outfilename, 'wb')
        outfp.write(infp.read())
        infp.close()
        outfp.close()
        return outfilename, coverimg

    def extract_images(self, outdir=''):
        """Extract all images in the book.
        """
        print("Extracting images from", self.filename, end=' ')
        if outdir:
            print("to", outdir)
        else:
            print()

        imagefiles = []

        for f in self.zip.namelist():
            ext = os.path.splitext(f)[-1].lower()
            if ext in self.image_exts:
                infp = self.zip.open(f)
                outfilename = os.path.join(outdir, os.path.basename(f))
                i = 1
                while os.path.exists(outfilename):
                    print(os.path.basename(outfilename), "already exists")
                    se = os.path.splitext(outfilename)
                    outfilename = se[0] + '-' + str(i) + se[1]
                outfp = open(outfilename, 'wb')
                outfp.write(infp.read())
                print("Extracted", f, "to", outfilename)
                imagefiles.append(outfilename)
                infp.close()
                outfp.close()

        return imagefiles


if __name__ == "__main__":
    def Usage():
        progname = os.path.basename(sys.argv[0])
        print("""Usage: %s file.epub [file.epub...] [-d] [-t tag1 [tag2...]]
       %s -T "New title" file.epub [file.epub...]
       %s -i [imagedir] file.epub [file.epub...]
Display, add or remove tags in epub ebooks,
or extract images from them.

Copyright 2012,2014 by Akkana Peck: share and enjoy under the GPL v2 or later.

Options:
    -t: add tags (otherwise, just print existing tags)
    -d: delete existing tags before adding new ones
    -b: print only one line for each book (useful with grep)
    -i [dir]: extract images into given directory (default .)"""
              % (progname, progname, progname))
        sys.exit(0)

    # optparse can't handle multiple arguments of the same type
    # (e.g. multiple tags), and the argparse doc is impenetrable.
    # So let's just do this: any argument corresponding to a readable
    # file must be an epub filename to be read/modified;
    # any argument following a -t is a tag to be added;
    # if there's a -d anywhere, we'll delete existing tags first;
    # if there's a -i anywhere, we'll extract images from the given book
    # (if the arg following -i is a directory, we'll extract to there);
    # any other flag, print a usage statement.

    imagedir = None
    extract_images = False
    epubfiles = []
    tags = []
    add_tags = False
    delete_tags = False
    change_title = False
    new_title = None
    brief = False
    for arg in sys.argv[1:]:
        if change_title and not new_title:
            new_title = arg
            continue
        if arg == '-d':
            delete_tags = True
            continue
        if arg == '-t':
            add_tags = True
            continue
        if arg.startswith('-T'):
            change_title = True
            if len(arg) > 2:
                new_title = arg[2:]
            continue
        if arg == '-b':
            brief = True
            continue
        if arg == '-i':
            extract_images = True
            imagedir = './'
            continue
        if arg == '-c':
            extract_images = "cover"
            imagedir = './'
            continue
        if arg[0] == '-':
            Usage()

        if change_title and not new_title:
            print("Must specify a new title with -T\n")
            Usage()

        # If we're here, the argument doesn't start with '-'.
        # It might still be the imagedir argument to -i, though.
        if imagedir == './':
            if os.path.isdir(arg):
                imagedir = arg
                continue
            elif not arg.endswith('.epub'):
                print("Argument after -i should be a directory "
                      "if it's not an EPUB book\n")
                Usage()

        if not add_tags:    # still adding files
            if os.access(arg, os.R_OK):
                epubfiles.append(arg)
            else:
                print("Can't read", arg, "-- skipping")
        else:               # done adding files, adding tags now
            tags.append(arg)

    if not epubfiles:
        Usage()

    for f in epubfiles:
        try:
            if not brief:
                print("=======")

            book = EpubBook()
            book.open(f)

            book.parse_contents()

            needs_save = False

            if imagedir is not None:
                if extract_images == "cover":
                    coverfile, zipname = book.extract_cover_image(imagedir)
                    if coverfile:
                        print("extracted cover to", coverfile)
                else:
                    book.extract_images(imagedir)
                book.close()
                continue

            if new_title:
                book.set_title(new_title)
                print("Set title to", new_title, "in", f)
                needs_save = True

            if delete_tags:
                book.delete_tags()
                needs_save = True

            if tags:
                print(f, ": old tags:", book.get_tags())
                book.add_tags(tags)
                needs_save = True

            if needs_save:
                book.save_changes()

            print(book.info_string(brief))

            book.close()
        except RuntimeError as e:
            print(e)
