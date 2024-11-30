#!/usr/bin/env python3

"""A TkInter Image Viewer.
   Suitable for embedding in larger apps, or use it by itself
   as a standalone image viewer.

   Copyright 2024 by Akkana -- Share and enjoy under the GPLv2 or later.
"""


import sys, os

import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, UnidentifiedImageError

VERBOSE = True

FRAC_OF_SCREEN = .85



def get_screen_width(root):
    return root.winfo_screenwidth(), root.winfo_screenheight()


class ImageViewerWidget:
    def __init__(self, root, img_list=[], size=None):
        """If size is omitted, the widget will be free to resize itself,
           otherwise it will try to fit itself in the space available.
        """
        self.img_list = img_list
        self.imgno = -1

        self.root = root    # Needed for queries like screen size

        self.fixed_size = size
        self.widget_size = size

        # The actual widget where images will be shown
        if size:
            self.lwidget = tk.Label(root, width=size[0], height=size[1])
        else:
            self.lwidget = tk.Label(root)
        self.lwidget.pack(fill="both", expand=True, padx=0, pady=0)

        self.lwidget.configure(background='black')


        self.cur_img = None
        self.rotation = 0

    def add_image(self, imgpath):
        """Add an image to the image list.
        """
        self.img_list.append(imgpath)

    def get_widget_size(self):
        return (self.lwidget.winfo_width(),
                self.lwidget.winfo_height())

    def set_size(self, newsize):
        """Change the size of the widget.
           Since this comes from callers outside the widget,
           allow it to override self.fixed_size.
        """
        if VERBOSE:
            print("set_size", newsize)

        if not newsize and not self.widget_size:
            self.widget_size = self.get_widget_size()
            if VERBOSE:
                print("Actual widget size:", self.widget_size)

        # This can be called many times, so don't do anything
        # if nothing changed since last time.
        elif newsize == self.widget_size:
            return

        if not self.widget_size or newsize > self.widget_size:
            # If it's increased, need to reload the current image
            # If there wasn't a widget_size before, might as well reload.
            if VERBOSE:
                print("Will reload current image")
            self.cur_img = None

        self.widget_size = newsize

        self.show_image()

    def show_image(self):
        """Show the current image.
           If self.cur_img is set, show that,
           otherwise, load a new one from self.img_list[self.imgno].
           Return 1 for success, 0 for valid image but not ready,
           -1 for invalid image or other error.
        """
        if VERBOSE:
            print("show_image, widget size is", self.widget_size)
        try:
            if not self.cur_img:
                self.cur_img = Image.open(self.img_list[self.imgno])
                self.rotation = 0
            if VERBOSE:
                print("Current image size:", self.cur_img.size)

            self.resize_to_fit()

            tkimg = ImageTk.PhotoImage(self.cur_img)
            self.lwidget.config(image=tkimg)
            self.lwidget.photo = tkimg

            # At this point,
            # self.lwidget.winfo_reqwidth(), self.lwidget.winfo_reqheight()
            # should be the size of the image,
            # though in practice it adds 2 pixels to both height and width.
            # self.lwidget.winfo_width(), self.lwidget.winfo_height()
            # is the size of the previous image, i.e. the current widget size,
            # except at the beginning where it's 1, 1

            if VERBOSE:
                print("Showing", self.img_list[self.imgno], '\n')

                # help(self.lwidget)
                # print("Current widget size:", self.lwidget.size())
                # print("size", self.lwidget.width, self.lwidget.height)
                # print("winfo size:", self.lwidget.winfo_width(), self.lwidget.winfo_height())
                # print("Requested size:", self.lwidget.winfo_reqwidth(), self.lwidget.winfo_reqheight())
                # print("Geometry:", self.lwidget.winfo_geometry())
                # print("Position:", self.lwidget.winfo_x(), self.winfo_y())

            return 1
        except FileNotFoundError:
            if VERBOSE:
                print(self.img_list[self.imgno], "not found",
                      file=sys.stderr)
            return -1
        except UnidentifiedImageError:
            if VERBOSE:
                print("Can't open", self.img_list[self.imgno], "as an image",
                      file=sys.stderr)
            return -1
        # except Exception as e:
        #     print("Some other exception:", e, "on", self.img_list[self.imgno],
        #           file=sys.stderr)
        #     return -1

        return -1

    def resize_to_fit(self):
        # self.cur_img must already exist
        if not self.cur_img:
            print("Internal error: resize_to_fit called before image loaded",
                  file=sys.stderr)
            return

        if self.root.attributes('-fullscreen'):    # fullscreen
            target_w, target_h = self.get_screen_width(self.root)
            if VERBOSE:
                print("resize_to_fit, fullscreen,", target_w, target_h)

        elif not self.fixed_size:                  # resizable
            if VERBOSE:
                print("Resizable widget")
            target_w = self.root.winfo_screenwidth() * FRAC_OF_SCREEN
            target_h = self.root.winfo_screenheight() * FRAC_OF_SCREEN
            if VERBOSE:
                print("resize_to_fit, variable height ->", target_w, target_h)

        else:                                      # fixed-size window
            target_w, target__h = self.widget_size
            if VERBOSE:
                print("resize_to_fit, fixed at", target_w, target_h)

        img_w, img_h = self.cur_img.size
        if img_w <= target_w and img_h <= target_h:
            if VERBOSE:
                print("Image (%dx%d) is already small enough for %dx%d"
                      % (img_w, img_h, target_w, target_h))
            return
        if VERBOSE:
            print("Resizing %dx%d to fit in %dx%d" % (img_w, img_h,
                                                      target_w, target_h))
        wratio = img_w / target_w
        hratio = img_h / target_h
        ratio = max(wratio, hratio)
        if VERBOSE:
            print("wratio", wratio, "hratio", hratio, "ratio", ratio)
            print("New size should be", int(img_w / ratio), int(img_h / ratio))
        self.cur_img = self.cur_img.resize(size=(int(img_w / ratio),
                                                 int(img_h / ratio)))
        print("Resized to", self.cur_img.size)


    def next_image(self):
        if not self.img_list:
            print("Error: no image list!")
            self.cur_img = None
            return

        while True:
            self.imgno += 1
            if self.imgno >= len(self.img_list):
                self.imgno = len(self.img_list) - 1
                if VERBOSE:
                    print("Can't go beyond last image")
                # Special case: if none of the images are viewable,
                # we'll get here without anything to show.
                if not self.cur_img:
                    print("Couldn't show any of the images", file=sys.stderr)
                    sys.exit(1)
                return
            if VERBOSE:
                print("  to", self.imgno, "->", self.img_list[self.imgno])
            self.cur_img = None
            loaded = self.show_image()
            if loaded == 1:
                return
            print("Couldn't show", self.img_list[self.imgno])

    def prev_image(self):
        if not self.img_list:
            print("Error: no image list!")
            return

        while True:
            self.imgno -= 1
            if self.imgno < 0:
                self.imgno = 0
                if VERBOSE:
                    print("Can't go before first image")
                return
            if VERBOSE:
                print("  to", self.imgno, "->", self.img_list[self.imgno])
            self.cur_img = None
            loaded = self.show_image()
            if loaded == 1:
                return
            print("Couldn't show", self.img_list[self.imgno])

    def rotate_right(self):
        if VERBOSE:
            print("Rotating right")
            print("  Before rotate, image size is", self.cur_img.size)
        self.cur_img = Image.open(self.img_list[self.imgno])
        self.rotation = (self.rotation + 270) % 360
        self.cur_img = self.cur_img.rotate(self.rotation, expand=True)
        if VERBOSE:
            print("  After rotate, image size is", self.cur_img.size)
        self.show_image()

    def rotate_left(self):
        if VERBOSE:
            print("Rotating right")
        self.cur_img = Image.open(self.img_list[self.imgno])
        self.rotation = (self.rotation + 90) % 360
        self.cur_img = self.cur_img.rotate(self.rotation, expand=True)
        self.show_image()

    def rotate_180(self):
        if VERBOSE:
            print("Rotating 180")
        # No need to reload, size isn't changing
        self.rotation = (self.rotation + 180) % 360
        self.cur_img = self.cur_img.rotate(self.rotation, expand=True)
        self.show_image()


class ImageViewerWindow:
    def __init__(self, img_list=[], width=0, height=0,
                 allow_resize=True, exit_on_q=True):

        self.root = tk.Tk()

        self.root.title("Pho Image Viewer")

        # To allow resizing, set self.fixed_size to None
        if allow_resize:
            self.fixed_size = None
        else:
            self.fixed_size = (1200, 900)
        self.viewer = ImageViewerWidget(self.root, img_list,
                                        size=self.fixed_size)

        self.root.bind('<Key-space>', self.next_image_handler)

        self.root.bind('<Key-BackSpace>', self.prev_image_handler)

        self.root.bind('<Key-Right>', self.rotate_right_handler)
        self.root.bind('<Key-Left>', self.rotate_left_handler)
        self.root.bind('<Key-Up>', self.rotate_180_handler)

        self.root.bind('<Key-f>', self.fullscreen_handler)
        self.root.bind('<Key-Escape>', self.fullscreen_handler)

        if self.fixed_size:
            self.root.bind("<Configure>", self.resize_handler)

        if exit_on_q:
            self.root.bind('<Key-q>', self.quit_handler)
            self.root.bind('<Control-Key-q>', self.quit_handler)

    def run(self):
        self.viewer.next_image()
        self.root.mainloop()

    def add_image(img):
        self.viewer.add_image(img)

    def next_image_handler(self, event):
        self.viewer.next_image()

    def prev_image_handler(self, event):
        self.viewer.prev_image()

    def rotate_right_handler(self, event):
        self.viewer.rotate_right()

    def rotate_left_handler(self, event):
        self.viewer.rotate_left()

    def rotate_180_handler(self, event):
        self.viewer.rotate_180()

    def resize_handler(self, event):
        if (event.width, event.height) != self.fixed_size:
            if self.fixed_size:
                print("Resize! New size is", event.width, event.height)
                self.fixed_size = (event.width, event.height)
                self.viewer.set_size(self.fixed_size)
                self.viewer.show_image()
            elif VERBOSE:
               print("Resize event, but who cares?")

    def fullscreen_handler(self, event):
        """f toggles, ESC gets out of fullscreen"""
        # Escape should always exit fullscreen
        if event.keysym == 'Escape':
            print("Escape")
            self.root.attributes("-fullscreen", False)

        # Else toggle
        else:
            if self.root.attributes('-fullscreen'): # already fullscreen
                # Come out of fullscreen
                self.root.attributes("-fullscreen", False)
                self.viewer.set_size(self.fixed_size)
                if VERBOSE:
                    print("Out of fullscreen, fixed_size is", self.fixed_size)
            else:
                # Into fullscreen
                self.root.attributes("-fullscreen", True)
                self.viewer.set_size((self.root.winfo_screenwidth(),
                                      self.root.winfo_screenheight()))
                if VERBOSE:
                    print("Now in fullscreen, size", self.viewer.widget_size)

        # viewer.set_size() should redraw as necessary

    def quit_handler(self, event):
        if VERBOSE:
            print("Bye")
        sys.exit(0)


if __name__ == '__main__':
    iv = ImageViewerWindow(sys.argv[1:])
    iv.run()

