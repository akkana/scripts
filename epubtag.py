#! /usr/bin/env python

import os, sys
import zipfile
import xml.dom.minidom

def tag_epub_file(filename, new_tag_list=None, delete_tags=False, brief=False) :
    subjectTag = 'dc:subject'
    if brief :
        print filename, '|',
    else :
        print filename
    if not zipfile.is_zipfile(filename) :
        print filename, "isn't an epub file (not zipped)"
        return
    zf = zipfile.ZipFile(filename)
    content = None
    for f in zf.namelist() :
        if os.path.basename(f) == 'content.opf' :
            contentfile = f
            content = zf.open(f)
            break
    if not content :
        raise RuntimeException('No content.opf in %s' % filename)

    # Now content is a file handle on the content.opf XML file
    try :
        dom = xml.dom.minidom.parse(content)
    except IOError, e :
        raise IOError, filename + ': ' + str(e)

    # Tags are inside <metadata> and look like this:
    # <metadata>
    #   <dc:subject>Presidents -- United States -- Biography</dc:subject>
    # Author (dc:creator) and Title (dc:title) are stored similarly.

    def get_matches(elname, delete_tags=False) :
        elements = dom.getElementsByTagName(elname)
        parent = None
        matches = []
        for el in elements :
            # Obviously there should be more error checking here
            if not parent :
                parent = el.parentNode
            else :
                assert parent == el.parentNode
            if delete_tags :
                print "Deleting:", el.childNodes[0].wholeText
                el.parentNode.removeChild(tag)
            else :
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

        return matches

    # But first, grab the title and author
    titles = get_matches('dc:title')
    if titles :
        if brief :
            print ', '.join(titles), '|',
        else :
            for t in titles :
                print "Title:", t
    authors = get_matches('dc:creator')
    if brief :
        print ', '.join(authors), '|',
    else :
        if len(authors) > 1 :
            print 'Authors:',
        else :
            print 'Author:',
        print ', '.join(authors)

    # Now get the subject tags.
    tags = get_matches(subjectTag, delete_tags)
    if brief :
        print ', '.join(tags)
    else :
        if tags :
            print "Tags:"
            for tag in tags :
                print '  ', tag

    # Now add new tags, if any
    content.close()
    if not new_tag_list :
        zf.close()
        return

    # If we didn't see a dc:subject, we still need a parent, the <metadata> tag.
    if not parent :
        parent = dom.getElementsByTagName("metadata")[0]
    # If there's no metadata tag, maybe we should add one,
    # but it might be better to throw an error.

    # There are new tags to add.
    # First, add them to the DOM by cloning the last node:
    for new_tag in new_tag_list :
        # Make the new node:
        #newnode = tag.cloneNode(False)
        newnode = dom.createElement(subjectTag)

        # Make a text node inside it:
        textnode = dom.createTextNode(new_tag)
        newnode.appendChild(textnode)

        # Also add a newline after each new node
        textnode = dom.createTextNode('\n')

        # Append nodenode after the last tag node we saw:
        if tag and tag.nextSibling :
            parent.insertBefore(textnode, tag.nextSibling)
            parent.insertBefore(newnode, textnode)
        # If we didn't see a tag, or the tag was the last child
        # of its parent, we have to do it this way:
        else :
            parent.appendChild(newnode)
            parent.appendChild(textnode)

        print "Adding:", new_tag

    # Open a new zip file to write to, and copy everything
    # but change the content.opf to the new one:
    new_epub_file = filename + '.tmp'
    ozf = zipfile.ZipFile(new_epub_file, 'w')
    for info in zf.infolist() :
        if os.path.basename(info.filename) == 'content.opf' :
            # dom.toprettyprintxml() returns unicode, which zipfile.writestr()
            # can't write. If you pass in encoding= then it works ...
            # but minidom gives us no way to find out the encoding
            # of the XML file we just parsed!
            # So the best we can do is force it to UTF-8,
            # barring re-opening the file and parsing the first line manually.
            # So crazy!
            encoding = 'UTF-8'
            ozf.writestr(info, dom.toprettyxml(encoding=encoding,
                                               newl=''))
            # This also works:
            #ozf.writestr(info, dom.toprettyxml().encode(encoding,
            #                                            'xmlcharrefreplace'))
        else :
            bytes = zf.read(info.filename)
            ozf.writestr(info, bytes)

    ozf.close()
    zf.close()

    # Now we have the new file in new_epub_file, old in filename.
    # Rename appropriately:
    bakfile = filename + ".bak"
    os.rename(filename, bakfile)
    os.rename(new_epub_file, filename)
    print "Wrote", filename
    os.remove(bakfile)

def Usage() :
    print "Usage: %s file.epub [file.epub...] [-d] [-t tag1 [tag2...]]" \
        % os.path.basename(sys.argv[0])
    print "Display, add or remove tags in epub ebooks."
    print "Copyright 2012 by Akkana Peck -- share and enjoy under the GPL."
    print "Options:"
    print "    -t: add tags (otherwise, just print existing tags)"
    print "    -d: delete existing tags before adding new ones"
    print "    -b: print only one line for each book (useful with grep)"
    sys.exit(1)

# main
if __name__ == "__main__" :
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
    for arg in sys.argv[1:] :
        if arg == '-d' :
            delete_tags = True
            continue
        if arg == '-t' :
            add_tags = True
            continue
        if arg == '-b' :
            brief = True
            continue
        if arg[0] == '-' :
            Usage()
        if not add_tags :    # still adding files
            if os.access(arg, os.R_OK) :
                epubfiles.append(arg)
            else :
                print "Can't read", arg, "-- skipping"
        else :               # done adding files, adding tags now
            tags.append(arg)

    if not epubfiles :
        Usage()

    for f in epubfiles :
        if not brief :
            print "======="
        tag_epub_file(f, tags, delete_tags, brief)
