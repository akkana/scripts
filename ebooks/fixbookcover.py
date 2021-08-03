#!/usr/bin/env python

# Add a book's title to the cover of an epub book.
# Useful for books such as Project Gutenberg that have a silly Palm picture
# with no words for a cover image.

import epubtag
import tempfile
import subprocess
import shutil
import sys, os
from PIL import Image
import gtk

import imageviewer

class BookCoverFixer:
    def __init__(self):
        self.book = None
        self.localcover = None
        self.coverzipname = None
        self.imagedir = tempfile.mkdtemp()
        self.newcoverfile = None

    def extract_cover(self, epubfile):
        self.book = epubtag.EpubBook()
        self.book.open(epubfile)
        self.book.parse_contents()

        self.localcover, self.coverzipname \
            = self.book.extract_cover_image(self.imagedir)
        if not self.localcover:
            # print "Couldn't find a cover in", epubfile
            self.localcover = None
            self.coverzipname = None

    def has_cover(self):
        return (self.book and self.localcover and self.coverzipname)

    def cleanup_tmp(self):
        if self.imagedir and os.path.exists(self.imagedir):
            shutil.rmtree(self.imagedir)

    def add_title_to_cover(self):
        """Actually do the fix"""

        # XXX figure out how to do this with imagemagick python bindings.
        # ImageMagick doesn't use the pretty font names with spaces in them;
        # use convert -list font to find out what font names it understands.
        # It doesn't understand aliases like "Serif", alas.
        # Times-New-Roman-Bold is fairly safe.
        #
        # XXX Would be nice to add ', '.join(self.book.get_authors())
        # in a smaller font, lower on the page.
        if self.has_cover():
            # New cover file should be in the same directory.
            self.newcoverfile = os.path.join(os.path.dirname(self.localcover),
                                  "new%s" % os.path.basename(self.localcover))
            # Get the image's size
            im = Image.open(self.localcover)
            width, height = im.size
            im.close()
            subprocess.call(["convert", "-background", "none",
                             "-fill", "black", "-stroke", "red",
                             "-gravity", "center",
                             "-size", "%dx%d" % (width, height),
                             "-font", "Times-New-Roman-Bold",
                             'caption:%s' % ', '.join(self.book.get_titles()),
                             self.localcover, "+swap",
                             "-composite", self.newcoverfile])
            print("Changed cover to %s" % self.newcoverfile)
            return self.newcoverfile

        # XXX Adding a new cover doesn't work yet.
        # I haven't figured out what I need to add to content.opf;
        # I've tried adding the relevant parts in metadata,
        # manifest, guide and spine and none of it works.
        print("WARNING: Adding new covers doesn't work yet")
        return None

        self.newcoverfile = "/tmp/cover.jpg"
        width, height = (480, 640)
        subprocess.call(["convert",
                         "-size", "%dx%d" % (width, height),
                         "-background", "white",
                         "-fill", "black", "-gravity", "center",
                         "-font", "Times-New-Roman-Bold",
                         "caption:%s" % ', '.join(self.book.get_titles()),
                         "-flatten", self.newcoverfile])

        return self.newcoverfile

    def save_changes(self):
        print("Saving changes, supposedly")
        print("Replacing %s with %s" % (self.coverzipname, self.newcoverfile))
        if self.has_cover():
            self.book.replace_file(self.coverzipname, self.newcoverfile)
        else:
            XXX
            metadata = self.book.dom.getElementsByTagName("metadata")[0]
            manifest = self.book.dom.getElementsByTagName("manifest")[0]

        self.book.save_changes()
        self.book.close()

#
# A GTK-based GUI window for doing this.
# imageviewer.ImageViewerWindow inherits from gtk.DrawingArea.
#
class BookCoverFixerWindow(imageviewer.ImageViewerWindow):
    def __init__(self, booklist):
        super(BookCoverFixerWindow, self).__init__(None, 300, 400)

        self.fixer = BookCoverFixer()

        self.booklist = booklist
        self.bookindex = -1

        self.add_title_label = "Add title"
        self.save_changes_label = "Save changes"

        hbox = gtk.HBox()
        self.do_btn = gtk.Button(self.add_title_label);
        hbox.pack_start(self.do_btn)
        self.do_btn.connect("clicked", self.do_fix)
        skip_btn = gtk.Button("Skip");
        hbox.pack_start(skip_btn)
        skip_btn.connect("clicked", self.next_book)
        self.main_vbox.pack_start(hbox)

        self.connect("key-press-event", self.key_press_event)

        self.expose_id = self.connect("expose-event", self.expose_handler)

    def do_fix(self, w=None):
        if self.do_btn.get_label() == self.add_title_label:
            self.add_title_to_cover()
        elif self.do_btn.get_label() == self.save_changes_label:
            self.fixer.save_changes()
            self.do_btn.set_label(self.add_title_label)
            self.next_book()

    def add_title_to_cover(self):
        if not self.fixer.has_cover():
            print("Eek, book wasn't initialized!")
        else:
            newcover = self.fixer.add_title_to_cover()
            if newcover:
                self.new_image(self.fixer.newcoverfile)
                self.viewer.draw_text("%s (unsaved)" % self.fixer.book.get_title())
                self.do_btn.set_label(self.save_changes_label)

    def quit(self):
        self.fixer.cleanup_tmp()
        super(BookCoverFixerWindow, self).quit()

    def next_book(self, w=None):
        self.bookindex += 1
        if self.bookindex >= len(self.booklist):
            self.quit()
            return
        self.do_btn.set_label(self.add_title_label)

        self.fixer.extract_cover(self.booklist[self.bookindex])

        if self.fixer.book:
            title = self.fixer.book.get_title()
        else:
            title = self.booklist[self.bookindex]

        if self.fixer.has_cover():
            self.new_image(self.fixer.localcover)
            self.viewer.draw_text("%s (unmodified)" % title)
            self.do_btn.set_sensitive(True)
        else:
            self.new_image(None)
            self.viewer.draw_text("No cover for %s" % title)
            self.do_btn.set_sensitive(False)
            return

    def expose_handler(self, widget, event):
        self.next_book()
        # We only want it the first time. The realize handler doesn't work
        # because it fires before the window actually exists.
        self.disconnect(self.expose_id)

    def key_press_event(self, widget, event, imagewin):
        """Handle a key press event anywhere in the window"""
        # Don't use space here: space will activate the focused button
        # rather than (or in addition to?) anything here.
        if event.string == "n":
            self.next_book();
            return
        if event.string == "y":
            self.do_fix()
            return
        if event.string == "q":
            self.quit()
            return

if __name__ == "__main__":
    fixer = BookCoverFixer()
    for arg in (sys.argv[1:]):
        fixer.extract_cover(arg)
        fixer.add_title_to_cover()
        fixer.save_changes()

    sys.exit(0)

    win = BookCoverFixerWindow(sys.argv[1:])
    win.run()
