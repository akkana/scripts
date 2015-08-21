#! /usr/bin/env python

# Utilities for reading epub books.
#
# Copyright 2015 by Akkana Peck. Share and enjoy under the GPL v2 or later.

import os, sys
import zipfile
import xml.dom.minidom

class EpubBook:
    subjectTag = 'dc:subject'

    def __init__(self):
        self.filename = None
        self.zip = None
        self.dom = None

    def open(self, filename):
        '''Open an epub file and set up handles to the zip archive
           and the DOM for the OPF file with all the metadata.
        '''
        if not zipfile.is_zipfile(filename):
            raise RuntimeError(filename + " isn't an epub file (not zipped)")

        self.filename = filename
        self.zip = zipfile.ZipFile(filename)

        # Parse the OPF file into self.dom.
        if not self.zip:
            raise RuntimeError('Epub book not opened')

        for f in self.zip.namelist():
            if os.path.basename(f).endswith('.opf'):
                self.contentfile = f
                content = self.zip.open(f)
                break
        if not content:
            raise RuntimeError('No .opf file in %s' % self.filename)
            return None

        # Now content is a file handle on the content.opf XML file
        try:
            self.dom = xml.dom.minidom.parse(content)
        except IOError, e:
            raise IOError, filename + ': ' + str(e)

        content.close()

    def close(self):
        self.zip.close()
        self.filename = None
        self.zip = None
        self.dom = None
 
    def get_matches(self, elname, delete_tags=False):
        '''Find matching tags in the OPF DOM.
        '''
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
                    print "Deleting:", el.childNodes[0].wholeText
                else:
                    print "Deleting empty", elname, "tag"
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
                matches.append(el.childNodes[0].wholeText.encode('utf-8',
                                                        'backslashreplace'))
            else:
                print "Empty", elname, "tag"

        return matches, elements, parent

    def get_titles(self):
        '''Get the title for this work. Returns a list since it's
           possible for an epub to have more than one title.
        '''
        titles, elements, parent = self.get_matches('dc:title')
        return titles

    def get_title(self):
        '''Get the first (perhaps only) title.
        '''
        return self.get_titles()[0]

    def get_authors(self):
        '''Get the list of authors (perhaps only one of them).
        '''
        authors, elements, parent = self.get_matches('dc:creator')
        return authors

    def get_tags(self):
        '''Get all tags in this epub book.
        '''
        # Tags are inside <metadata> and look like this:
        # <metadata>
        #   <dc:subject>Presidents -- United States -- Biography</dc:subject>
        # Author (dc:creator) and Title (dc:title) are stored similarly.

        tags, elements, parent = self.get_matches(self.subjectTag)
        return tags

    def info_string(self, brief=False):
        '''Return an info string describing this book, suitable for printing.
        '''
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
                outstr += "Tags: "
                for tag in tags:
                    outstr += '\n   ' + tag

        return outstr

    def delete_tags(self):
        '''Delete all tags in the book.
        '''
        tags, elements, parent = self.get_matches(self.subjectTag, True)

    def add_tags(self, new_tag_list):
        '''Add the given tags to any tags the epub already has.
        '''
        tags, elements, parent = self.get_matches(self.subjectTag)

        # If we didn't see a dc:subject, we still need a parent,
        # the <metadata> tag.
        if not parent:
            print "Warning: didn't see any subject tags previously"
            parent = self.dom.getElementsByTagName("metadata")[0]

            # If there's no metadata tag, maybe we should add one,
            # but it might be better to throw an error.
            if not parent:
                raise RuntimeError("No metadata tag! Bailing.")

        # We'll want to add the new subject tags after the last one.
        if elements:
            last_tag_el = elements[-1]
        else:
            last_tag_el = None

        for new_tag in new_tag_list:
            # Make the new node:
            #newnode = tag.cloneNode(False)
            newnode = self.dom.createElement(self.subjectTag)

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

            print "Adding:", new_tag

    def save_changes(self):
        '''Overwrite the old file with any changes that have been
           made to the epub's tags. The old file will be backed
           up in filename.bak.
        '''
        # Open a new zip file to write to, and copy everything
        # but change the content.opf (or whatever.opf) to the new one:
        new_epub_file = self.filename + '.tmp'
        ozf = zipfile.ZipFile(new_epub_file, 'w')
        for info in self.zip.infolist():
            if info.filename.endswith('.opf'):
                # dom.toprettyprintxml() returns unicode, which
                # zipfile.writestr() can't write. If you pass in
                # encoding= then it works ... but minidom gives us
                # no way to find out the encoding of the XML file
                # we just parsed! So the best we can do is force
                # it to UTF-8, barring re-opening the file and
                # parsing the first line manually. So crazy!
                encoding = 'UTF-8'
                ozf.writestr(info, self.dom.toprettyxml(encoding=encoding,
                                                   newl=''))
                # This also works:
                # ozf.writestr(info,
                #              self.dom.toprettyxml().encode(encoding,
                #                                      'xmlcharrefreplace'))
            else:
                # For every other file, just copy directly.
                ozf.writestr(info, self.zip.read(info.filename))

        ozf.close()

        # Now we have the new file in new_epub_file, old in filename.
        # Rename appropriately:
        bakfile = self.filename + ".bak"
        os.rename(self.filename, bakfile)
        os.rename(new_epub_file, self.filename)
        print "Wrote", self.filename
        os.remove(bakfile)

# main
if __name__ == "__main__":

    def Usage():
        print "Usage: %s file.epub [file.epub...] [-d] [-t tag1 [tag2...]]" \
            % os.path.basename(sys.argv[0])
        print "Display, add or remove tags in epub ebooks."
        print "Copyright 2012 by Akkana Peck -- share and enjoy under the GPL."
        print "Options:"
        print "    -t: add tags (otherwise, just print existing tags)"
        print "    -d: delete existing tags before adding new ones"
        print "    -b: print only one line for each book (useful with grep)"
        sys.exit(1)

    # optparse can't handle multiple arguments of the same type
    # (e.g. multiple tags), and the argparse doc is impenetrable.
    # So let's just do this: any argument corresponding to a readable
    # file must be an epub filename to be read/modified;
    # any argument following a -t is a tag to be added;
    # if there's a -d anywhere, we'll delete existing tags first;;
    # any other flag, print a usage statement.

    epubfiles = []
    tags = []
    add_tags = False
    delete_tags = False
    brief = False
    for arg in sys.argv[1:]:
        if arg == '-d':
            delete_tags = True
            continue
        if arg == '-t':
            add_tags = True
            continue
        if arg == '-b':
            brief = True
            continue
        if arg[0] == '-':
            Usage()
        if not add_tags :    # still adding files
            if os.access(arg, os.R_OK):
                epubfiles.append(arg)
            else:
                print "Can't read", arg, "-- skipping"
        else :               # done adding files, adding tags now
            tags.append(arg)

    if not epubfiles:
        Usage()

    for f in epubfiles:
        try:
            if not brief:
                print "======="

            book = EpubBook()
            book.open(f)

            if delete_tags:
                book.delete_tags()

            if tags:
                book.add_tags(tags)

            if tags or delete_tags:
                book.save_changes()

            print book.info_string(brief)

            book.close()
        except RuntimeError, e:
            print e
