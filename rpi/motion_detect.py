#!/usr/bin/env python

# Detect motion or change between successive camera images.
# Snap a higher resolution photo when something has changed.

# Uses code originally from brainflakes in this thread:
# www.raspberrypi.org/phpBB3/viewtopic.php?f=43&t=45235

# Copyright (C) 2014 Akkana Peck <akkana@shallowsky.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from piphoto import take_still

from PIL import Image

class MotionDetector:
    def __init__(self,
                 test_res=[320, 240], threshold=30, sensitivity=20,
                 test_borders=None,
                 verbose=0):
        '''test_res: resolution of test images to be compared.
              XXX Can't we get that from the images passed in?
           threshold: How different does a pixel need to be?
           sensitivity: How many pixels must change?
           verbose: 0 = quiet, 1 = chatter on stdout, 2 = save debug pics

           test_borders: [ [ [left, right], [top, bottom] ], ... ]
             testBorders are NOT zero-based, the first pixel is 1
             and the last pixel is testWidth or testHeight

             You can define areas to scan for changed pixels.
             For example, if your picture looks like this:

                 ....XXXX
                 ........
                 ........

             "." is a street or a house,
             "X" are trees which move like crazy when the wind is blowing,
             to prevent constant photos, your setting might look like this:

             testBorders = [ [[1,50],[1,75]], [[51,100],[26,75]] ]
             area y=1 to 25 not scanned in x=51 to 100

             Even more complex example
             testBorders = [ [[1,39],[1,75]], [[40,67],[43,75]],
                             [[68,85],[48,75]], [[86,100],[41,75]] ]
        '''
        self.test_res = test_res
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.verbose = verbose

        self.bufold = None

        # What area of the image should we scan for changes?
        # Default setting (if None passed in): use whole image.
        if not test_borders:
            self.test_borders = [ [[1,test_res[0]],[1,test_res[1]]] ]
        else:
            self.test_borders = test_borders

    def compare_images(self, new_image):
        '''Compare an image with the previous one,
           and return True if we think they differ enough.
           Image is a PIL.Image.
           We'll remember the pixel data from the previous image.
        '''
        # Is this the first time?
        if not self.bufold:
            self.bufold = new_image.load()
            return False

        bufnew = new_image.load()

        # if debugimage:
        if (self.verbose > 1):
            debugimage = new_image.copy()
            debug_buf = debugimage.load()
        else:
            debug_buf = None

        changed_pixels = 0
        for piece in self.test_borders:
            for x in xrange(piece[0][0]-1, piece[0][1]):
                for y in xrange(piece[1][0]-1, piece[1][1]):

                    # Just check green channel as it's the highest quality
                    pixdiff = abs(bufnew[x,y][1] - self.bufold[x,y][1])
                    if pixdiff > self.threshold:
                        changed_pixels += 1
                        # If debugging, rewrite changed pixels -> green
                        if (debug_buf):
                            debug_buf[x,y] = (0, 255, 0)

        changed = changed_pixels > self.sensitivity

        if debug_buf:
            # If we consider the image to have changed,
            # draw blue and white borders around each test area.
            if changed:
                halfwidth = 1
                for piece in self.test_borders:
                    for x in xrange(piece[0][0]-1, piece[0][1]):
                        if piece[1][0] > 1:
                            debug_buf[x, piece[1][0]-2]  = (255, 255, 255)
                        debug_buf[x, piece[1][0]-1]  = (0, 0, 255)
                        debug_buf[x, piece[1][1]-1]  = (0, 0, 255)
                        debug_buf[x, piece[1][1]]  = (255, 255, 255)
                    for y in xrange(piece[1][0]-1, piece[1][1]):
                        if piece[0][0] > 1:
                            debug_buf[piece[0][0]-2, y]  = (255, 255, 255)
                        debug_buf[piece[0][0]-1, y]  = (0, 0, 255)
                        debug_buf[piece[0][1]-1, y]  = (0, 0, 255)
                        debug_buf[piece[0][1], y]  = (255, 255, 255)

            debugimage.save("/tmp/debug.png") # save debug image as bmp
            print "debug.png saved, %s changed pixel" % changed_pixels

        if self.verbose:
            if changed:
                print "=====================",
            print changed_pixels, "pixels changed"

        self.bufold = bufnew
        return changed

if __name__ == '__main__':
    import time

    test_res=[320, 240]
    test_borders = [ [ [140, 180], [105, 135] ] ]
    md = MotionDetector(test_res=test_res, test_borders=test_borders)

    bufnew = None
    bufold = None
    while True:
        print "Taking a still ..."
        if use_tmp_file:
            tmpfile = "/tmp/still.jpg"
            take_still(outfile=tmpfile, res=test_res, verbose=True)
            im = Image.open(tmpfile)
        else:   # keep it all in memory, no temp files
            img_data = take_still(outfile='-', res=test_res, verbose=True)
            im = Image.open(imageData)

        print "Took it!", tmpfile
        different = md.compare_images(im)
        imageData.close()
        if different:
            print "They're different!"

        time.sleep(5)

