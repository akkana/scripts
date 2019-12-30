#!/usr/bin/env python

import gtk, glib
import pango
import gc

class ImageViewer(gtk.DrawingArea):
    """A generic PyGTK image viewer widget
    """

    def __init__(self):
        super(ImageViewer, self).__init__()
        self.connect("expose-event", self.expose_handler)
        self.xgc_bg = None
        self.xgc_fg = None
        self.pixbuf = None
        self.label_text = None
        self.width = None
        self.height = None
        self.cur_img = None
        self.width = None
        self.height = None

    def expose_handler(self, widget, event):
        if not self.xgc_bg:
            self.xgc_bg = widget.window.new_gc()
            self.xgc_bg.set_rgb_fg_color(gtk.gdk.Color(0, 0, 0))

            self.xgc_fg = widget.window.new_gc()
            self.xgc_fg.set_rgb_fg_color(gtk.gdk.color_parse("yellow"))

            x, y, w, h = self.get_allocation()

            if w != self.width or h != self.height:
                # get_allocation() gives a number that's too large,
                # and if we later try to draw_rectangle() with these
                # dimensions, we'll only get half the rectangle horizontally.
                # I have no idea why this is happening, but subtracting a
                # few pixels from allocation width is a temporary workaround.
                self.width = w    # -5
                self.height = h

            # Have we had load_image called, but we weren't ready for it?
            # Now, theoretically, we are ... so call it again.
            if w and h and self.cur_img and not self.pixbuf:
                self.prepare_image()

        self.show_image()

    def resize(self, new_w, new_h):
        if new_w == self.width and new_h == self.height:
            return
        self.width = new_w
        self.height = new_h
        self.prepare_image()
        self.show_image()

    # Mapping from EXIF orientation tag to degrees rotated.
    # http://sylvana.net/jpegcrop/exif_orientation.html
    exif_rot_table = [ 0, 0, 180, 180, 270, 270, 90, 90 ]
    # Note that orientations 2, 4, 5 and 7 also involve a flip.
    # We're not implementing that right now, because nobody
    # uses it in practice.

    def load_image(self, img):
        self.cur_img = img
        if self.width and self.height:
            if self.cur_img:
                self.prepare_image()
            else:
                self.pixbuf = None
                self.clear()

        self.label_text = None

    def prepare_image(self):
        """Load the image passed in, and show it.
           img is a filename.
           Return True for success, False for error.
        """

        self.label_text = None

        # Clean up memory from any existing pixbuf.
        # This still needs to be garbage collected before returning.
        if self.pixbuf:
            self.pixbuf = None

        try:
            newpb = gtk.gdk.pixbuf_new_from_file(self.cur_img)

            # We can't do any of the rotation until the window appears
            # so we know our window size.
            # But we have to load the first pixbuf anyway, because
            # otherwise we may end up pointing to an image that can't
            # be loaded. Super annoying! We'll end up reloading the
            # pixbuf again after the window appears, so this will
            # slow down the initial window slightly.
            if not self.width:
                return True

            # Do we need to check rotation info for this image?
            # Get the EXIF embedded rotation info.
            orient = newpb.get_option('orientation')
            if orient is None :    # No orientation specified; use 0
                orient = 0
            else :                 # convert to int array index
                orient = int(orient) - 1
            rot = self.exif_rot_table[orient]

            # Scale the image to our display image size.
            # We need it to fit in the space available.
            # If we're not changing aspect ratios, that's easy.
            oldw = newpb.get_width()
            oldh = newpb.get_height()
            if rot in [ 0, 180]:
                if oldw > oldh :     # horizontal format photo
                    neww = self.width
                    newh = oldh * self.width / oldw
                else :               # vertical format
                    newh = self.height
                    neww = oldw * self.height / oldh

            # If the image needs to be rotated 90 or 270 degrees,
            # scale so that the scaled width will fit in the image
            # height area -- even though it's still width because we
            # haven't rotated yet.
            else :     # We'll be changing aspect ratios
                if oldw > oldh :     # horizontal format, will be vertical
                    neww = self.height
                    newh = oldh * self.height / oldw
                else :               # vertical format, will be horiz
                    neww = self.width
                    newh = oldh * self.width / oldw

            # Finally, do the scale:
            newpb = newpb.scale_simple(neww, newh,
                                             gtk.gdk.INTERP_BILINEAR)

            # Rotate the image if needed
            if rot != 0:
                newpb = newpb.rotate_simple(rot)

            # newpb = newpb.apply_embedded_orientation()

            self.pixbuf = newpb

            loaded = True

        except glib.GError:
            print "GError"
            self.pixbuf = None
            loaded = False

        # garbage collect the old pixbuf, if any, and the one we just read in:
        newpb = None
        gc.collect()

        return loaded

    def show_image(self):
        if not self.xgc_bg:
            print "show_image: xgc not ready yet"
            return

        self.clear()

        if self.pixbuf:
            # Center it:
            x = (self.width - self.pixbuf.get_width()) / 2
            y = (self.height - self.pixbuf.get_height()) / 2
            self.window.draw_pixbuf(self.xgc_bg, self.pixbuf, 0, 0, x, y)

        if self.label_text:
            self.draw_text(self.label_text)

        if not self.pixbuf and not self.label_text:
            self.draw_text("No image")

    # def rotate(self, rot):
    #     self.cur_img.rot = (self.cur_img.rot + rot + 360) % 360
    #     # XXX we don't always need to reload: could make this more efficient.
    #     self.load_image(self.cur_img)

    def clear(self):
        if not self.xgc_bg:
            return

        self.window.draw_rectangle(self.xgc_bg, True,
                                   0, 0, self.width, self.height)

    def draw_text(self, label):
        if not self.xgc_fg:
            print "draw_text: xgc not ready yet"
            return
        # self.pixbuf = None
        self.label_text = label
        # It never fails to amaze me how baroque it is to draw text in pygtk:
        layout = self.create_pango_layout(label)
        font_desc = pango.FontDescription("Sans Bold 18")
        layout.set_font_description(font_desc)
        layout.set_width(self.width * pango.SCALE)
        layout.set_wrap(pango.WRAP_WORD)
        label_width, label_height = layout.get_pixel_size()
        offset = 3
        self.window.draw_layout(self.xgc_bg,
                                self.width - label_width + offset,
                                self.height - label_height + offset,
                                layout)
        self.window.draw_layout(self.xgc_fg,
                                self.width - label_width,
                                self.height - label_height,
                                layout)

class ImageViewerWindow(gtk.Window):
    """Bring up a window that can view images.
    """

    def __init__(self, file_list=None, width=1024, height=768):
        super(ImageViewerWindow, self).__init__(gtk.WINDOW_TOPLEVEL)
        self.file_list = file_list
        self.imgno = 0

        # The size of the image viewing area:
        self.width = width
        self.height = height

        self.isearch = False

        self.set_border_width(10)

        self.connect("delete_event", gtk.main_quit)
        self.connect("destroy", gtk.main_quit)

        self.main_vbox = gtk.VBox(spacing=4)

        self.viewer = ImageViewer()
        self.viewer.connect("configure_event", self.configure_event)

        self.main_vbox.pack_start(self.viewer)

        self.add(self.main_vbox)

        self.resize(self.width, self.height)

        # Realize apparently happens too early.
        # self.connect("realize", self.expose_handler)

        if self.file_list:
            self.viewer.load_image(self.file_list[0])

    def run(self):
        self.show_all()
        gtk.main()

    # configure event is registered on the viewer, not the window.
    def configure_event(self, widget, event):
        # vx, vy, vw, vh = self.viewer.get_allocation()
        x, y, self.width, self.height = self.get_allocation()
        self.viewer.resize(event.width, event.height)

    def new_image(self, imgfile):
        self.file_list = [ imgfile ]
        self.imgno = 0
        self.viewer.load_image(imgfile)
        if imgfile:
            self.viewer.show_image()

    def next_image(self):
        self.imgno = (self.imgno + 1) % len(self.file_list)
        self.viewer.load_image(self.file_list[self.imgno])
        self.viewer.show_image()

    def quit(self):
        gtk.main_quit()

def key_press_event(widget, event, imagewin):
    """Handle a key press event anywhere in the window"""
    if event.string == " ":
        imagewin.next_image()
        return
    if event.string == "q":
        gtk.main_quit()
        return

if __name__ == "__main__":
    import sys
    win = ImageViewerWindow(sys.argv[1:])
    win.connect("key-press-event", key_press_event, win)
    win.run()
