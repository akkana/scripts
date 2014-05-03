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

import os, sys
import time
import datetime
import re
import subprocess

class MotionDetector:
    def __init__(self,
                 test_res=[320, 240], threshold=30, sensitivity=20,
                 test_borders=None, full_res=None,
                 localdir=None, remotedir=None,
                 crop=False, verbose=0):
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
           crop: you may pass in a WxH+X+Y specifier, False (don't crop
               at all), or '-' (crop to match the test borders)
        '''
        self.test_res = test_res
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.verbose = verbose
        self.localdir = localdir
        self.remotedir = remotedir
        self.full_res = full_res

        self.bufold = None

        # What area of the image should we scan for changes?
        # Default setting (if None passed in): use whole image.
        if not test_borders:
            self.test_borders = [ [[1,test_res[0]],[1,test_res[1]]] ]
        else:
            self.test_borders = test_borders

        # Find a crop rectangle that includes all the test borders.
        # XXX Should move crop functionality to piphoto.py
        # and then it can let fswebcam do the work.
        if crop == '-':
            left = test_res[0]
            right = 0
            top = test_res[1]
            bottom = 0
            for piece in self.test_borders:
                left = min(left, piece[0][0])
                right = max(right, piece[0][1])
                top = min(top, piece[1][0])
                bottom = max(bottom, piece[1][1])

            # Sanity check:
            if left > 0 and right > left and right < test_res[0] and \
                    top > 0 and bottom > top and bottom < test_res[1]:

                # But wait! We aren't done. The crop rectangle has to be
                # scaled up to the full resolution of the image,
                # we have no way of knowing what our final res is --
                # even if we specify one, the camera may decide otherwise.
                # The only way, apparently, is to take a full-res photo
                # and see how big it comes out. And hope that doesn't change.
                img_data = take_still(outfile='-', res=full_res, format='jpg',
                                      verbose=self.verbose)
                im = Image.open(img_data)
                self.full_res = im.size
                print "Using full resolution of %d x %d" % self.full_res
                img_data = None
                im = None
                convX = self.full_res[0] / self.test_res[0]
                convY = self.full_res[1] / self.test_res[1]
                self.crop = '%dx%d+%d+%d' % ((right-left)*convX,
                                             (bottom-top)*convY,
                                             left*convX, top*convY)
                if self.verbose:
                    print "Cropping to test borders", self.crop
            else:
                print "Not cropping: problem finding borders of test area:", \
                    left, right, top, bottom
                self.crop = False
        else:
            self.crop = crop    # Should be either False, or a specifier
            if self.verbose:
                if self.crop:
                    print "Not cropping"
                else:
                    print "Cropping to", self.crop

        sys.exit(0)

    def compare_images(self, new_image):
        '''Compare an image with the previous one,
           and return True if we think they differ enough.
           Image is a PIL.Image.
           We'll remember the pixel data from the previous image.
        '''
        # # Is this the first time?
        # if not self.bufold:
        #     self.bufold = new_image.load()
        #     return False, new_image

        bufnew = new_image.load()

        # if debugimage:
        if (self.verbose > 1):
            debugimage = new_image.copy()
            debug_buf = debugimage.load()
        else:
            debugimage = None
            debug_buf = None

        changed_pixels = 0
        if self.bufold:
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
        else:
            print "First time, forcing a snap"
            changed = True

        if debug_buf:
            # Draw blue borders around the test areas no matter what,
            # and add white borders if something has changed.
            for piece in self.test_borders:
                for x in xrange(piece[0][0]-1, piece[0][1]):
                    debug_buf[x, piece[1][0]-1]  = (0, 0, 255)
                    debug_buf[x, piece[1][1]-1]  = (0, 0, 255)
                    if changed:
                        if piece[1][0] > 1:
                            debug_buf[x, piece[1][0]-2]  = (255, 255, 255)
                            debug_buf[x, piece[1][1]]  = (255, 255, 255)
                for y in xrange(piece[1][0]-1, piece[1][1]):
                    debug_buf[piece[0][0]-1, y]  = (0, 0, 255)
                    debug_buf[piece[0][1]-1, y]  = (0, 0, 255)
                    if changed:
                        debug_buf[piece[0][1], y]  = (255, 255, 255)
                        if piece[0][0] > 1:
                            debug_buf[piece[0][0]-2, y]  = (255, 255, 255)

            # debugimage.save("/tmp/debug.png") # save debug image as bmp
            # print "debug.png saved, %s changed pixel" % changed_pixels

        if changed:
            print "=====================", changed_pixels, "pixels changed"
        elif self.verbose:
            print changed_pixels, "pixels changed"

        if not self.bufold:
            fileroot = 'first'
            print "Saving initial image"
        else:
            fileroot = 'snap'
        self.bufold = bufnew

        if changed and self.localdir:
            # If they're different, snap a high-res photo.
            # Upload it if possible, otherwise save it locally.
            # Check it every time, since the network might go downls.
            if self.remotedir and os.access(self.remotedir, os.W_OK):
                snapdir = self.remotedir
            else:
                snapdir = self.localdir
            if snapdir:
                now = datetime.datetime.now()
                snapfile = '%s-%02d-%02d-%02d-%02d-%02d-%02d.jpg' % \
                    (fileroot,
                     now.year, now.month, now.day,
                     now.hour, now.minute, now.second)
                snappath = os.path.join(snapdir, snapfile)

                if self.crop:
                    # Snap data to memory, then pass it to jpegtran to crop.
                    # jpegtran can only write to stdout so we'll have to
                    # write it to the file ourselves.
                    if self.verbose:
                        print "Cropping"
                    img_data = take_still(outfile='-', res=self.full_res,
                                          format='jpg', verbose=self.verbose)
                    # img_data is a StringIO instance.
                    # But Popen can't take a StringIO as input;
                    # instead, have to write the data into a pipe.
                    p = subprocess.Popen(['/usr/bin/jpegtran',
                                          '-crop', self.crop],
                                         shell=False,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE)
                    # Better to use communicate() than write()
                    img_data = p.communicate(input=img_data.getvalue())[0]
                    # Or use img_data.read() instead of getvalue --
                    # not clear if there's any efficiency difference
                    # since we have to keep the whole string in mem either way.
                    p.stdin.close()
                    snapout = open(snappath, 'w')
                    snapout.write(img_data)
                    snapout.close()
                    p = None
                    print "Saved cropped still", snappath
                else:
                    take_still(outfile=snappath, res=self.full_res,
                               verbose=self.verbose)
                    print "Saving to", snappath

        return changed, debugimage

if __name__ == '__main__':
    # Usage: motion_detect.py [-c] [-v] localdir [remotedir]
    import argparse

    parser = argparse.ArgumentParser(description="""Monitor a camera and snap photos when something has changed.

Example: motion_detect.py -v -r 320x240 -c 150x150+100+50 -b 50x50+125+75 /tmp /mnt/server/pix

Copyright 2014 by Akkana Peck; share and enjoy under the GPL v2 or later.""",
                         formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("-s", "--sensitivity", type=int,
        help="Sensitivity: How many pixels must change?")
    parser.add_argument("-t", "--threshold", type=int,
        help="Threshold: How different does a pixel need to be?")
    parser.add_argument("-r", "--resolution", default='320x240',
        help="Resolution of the test image (WxH). Default 320x240.")
    parser.add_argument("-f", "--fullres",
        help="""Full resolution to save images.
Defaults to the resolution of the camera if we can get it.
Actual resolution may be different if the camera can't take a photo
at the specified resolution.""")
    parser.add_argument("-b", "--borders",
                        help="""Borders of the test region we'll monitor.
A colon-separated list of wxh+x+y identifiers.
E.g. 100x50:5:20:100x50:200:150""")

    # --crop can either be omitted (don't crop at all), included without
    # an additional argument (crop to the test border boundaries),
    # or included with its own WxH+X+Y specifier.
    # With a default=False and nargs='?', argparse gives us False if -c
    # isn't specified, None if it's specified with no argument, otherwise
    # the argument that follows it.
    parser.add_argument("-c", "--crop", nargs='?', default=False,
                        help="""Crop full-resolution images.
You can specify a crop region as WxH+0+0 (with the coordinates relative
to the test image size, not the final image size).
Specifying -c - or omitting the region specifier will result in
a crop to the boundaries of the test region.""")

    parser.add_argument("-v", "--verbose", action='store_true', default=False,
        help="Verbose: chatter about what the program is doing.")

    parser.add_argument("localdir")
        # type=argparse.FileType('w')
    parser.add_argument("remotedir", nargs='?')
    
    args = parser.parse_args()
    print args
    print
    print "Crop:", args.crop

    def resparse(res_str, default_res=None):
        if not res_str:
            return default_res
        try:
            parsed_res = map(int, res_str.split('x'))
        except ValueError:
            print "Please specify resolution as WxH"
            sys.exit(1)
        if len(parsed_res) != 2:
            print "Please specify resolution as WxH"
            sys.exit(1)
        return parsed_res

    test_res = resparse(args.resolution, [320, 240])
    print "Using test resolution of", test_res

    full_res = resparse(args.fullres, None)
    if full_res:
        print "Saving stills using full resolution of", full_res
    else:
        print "Will try to use full resolution of camera for saved stills"

    if args.borders:
        test_borders = []
        border_list = args.borders.split(':')
        # Each item in border_list is a WxH+x+y
        for b in border_list:
            match = re.search('(\d+)x(\d+)\+(\d+)\+(\d+)', b)
            if not match:
                print "Couldn't parse", b, ": please specify borders as WxH+X+Y"
                sys.exit(1)
            match = map(int, match.groups())
            if len(match) != 4:
                print "Need four items, WxH+X+Y, in", b
                sys.exit(1)
            # Now match is (w, h, x, y).
            # We need to turn that into [[x0, x1], [y0, y1]].
            # XXX There is an off-by-one error because the original brainflakes
            # XXX code uses 1 as its array boundary. Fix this!
            test_borders.append([[match[2], match[2]+match[0]],
                                 [match[3], match[3]+match[1]]])
        print "Using test borders:", test_borders
    else:
        # test_borders = [ [ [60, 200], [125, 190] ] ]
        test_borders = None
        if args.verbose:
            print "No test region, using full image"

    # If a crop region is specified, make sure it at least parses.
    if args.crop == None:
        args.crop = '-'
    elif args.crop and args.crop != '-':
        check_crop = resparse(args.crop)
    # else it's False, meaning don't crop

    if args.verbose:
        print
        print "Parameters:"
        for param in ('sensitivity', 'threshold', 'resolution', 'fullres',
                      'borders', 'crop', 'verbose', 'localdir', 'remotedir'):
            if vars(args)[param]:
                print '  %s: %s' % (param, vars(args)[param])
            else:
                print '  %s not specified' % param
        print

    md = MotionDetector(test_res=test_res,
                        threshold=args.threshold, sensitivity=args.sensitivity,
                        test_borders=test_borders,
                        full_res=args.fullres,
                        localdir=args.localdir,
                        remotedir=args.remotedir,
                        crop=args.crop, verbose=args.verbose)

    # We want the full snapshots to use the full resolution of the camera.
    # fswebcam has no way to do that, and no way to check first,
    # so we specify a res that's too high and let it adjust downward.

    try:
        while True:
            use_tmp_file = False
            if use_tmp_file:
                tmpfile = "/tmp/still.jpg"
                take_still(outfile=tmpfile, res=test_res,
                           verbose=args.verbose)
                im = Image.open(tmpfile)
            else:   # keep it all in memory, no temp files
                img_data = take_still(outfile='-', res=test_res,
                                      verbose=args.verbose)
                im = Image.open(img_data)

            different, debugimage = md.compare_images(im)
            img_data.close()

            time.sleep(5)
    except KeyboardInterrupt:
        print "Interrupt: exiting"

