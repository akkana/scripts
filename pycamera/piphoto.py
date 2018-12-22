#!/usr/bin/env python

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

#
# Take a still photo. If a USB camera is attached (/dev/video0), use it,
# else if a PiCam is attached (/dev/fb0), use that instead,
# else throw an exception.
#

from __future__ import print_function

import os, sys
import subprocess
import time
# import StringIo
import io
from PIL import Image

# Used to import this in PiCamera's __init__, but then the module
# isn't available outside that function.
# So we need to import it here and use a global variable, sigh.
try:
    import picamera
    use_picamera = True
except ImportError:
    use_picamera = False

class PiCamera:

    def __init__(self, verbose=False):
        self.verbose = verbose

        self.use_picamera = use_picamera
        if self.verbose:
            if use_picamera:
                print("Using picamera module")
            else:
                print("Using raspistill")

    def camera_present(self):
        '''Is there a Pi camera module plugged in and accessible?
        '''
        camdet = subprocess.check_output(["vcgencmd","get_camera"])
        # Returns something like: supported=0 detected=0
        # Strip the newline and check only the last character:
        if int(camdet.strip()[-1]):
            return True
        return False

    def take_still(self, outfile='/tmp/still.jpg',
                   res=[640, 480], format=None):
        if self.use_picamera:
            return self.take_still_picamera(outfile, res, format)
        else:
            return self.take_still_shell(outfile, res, format)

    def take_still_shell(self, outfile='/tmp/still.jpg',
                         res=[640, 480], format=None):
        '''Take a still photo by calling raspistill.
           If outfile is '-' then we will take a photo to memory
           and return the buffer in a format suitable for PIL.
        '''
        if not os.path.exists('/usr/bin/raspistill'):
            raise SystemError("Neither python-picamera nor raspistill is installed")
        if self.verbose:
            print("Taking photo with raspistill")
        args = ['/usr/bin/raspistill', '-n', '-o', outfile]
        if res:
            args.append('-w')
            args.append(str(res[0]))
            args.append('-h')
            args.append(str(res[1]))
        # Was hoping that increasing sharpness would help quality, but no.
        # if not res or res[1] >= 1600:
        #     args.append('-sh')
        #     args.append('100')
        if self.verbose:
            print("Calling:", args)

        # If the outfile is specified as -, we want raw data.
        # PIL expects bmp data, apparently.
        if outfile == '-':
            args.append('-e')
            if format:
                if self.verbose:
                    print("Using", format, "format")
                args.append(format)
            else:
                if self.verbose:
                    print("No format specified, falling back to BMP")
                args.append('bmp')   # should compare png performance

            image_data = io.StringIO()
            image_data.write(subprocess.check_output(args))
            image_data.seek(0)
            return image_data

        rv = subprocess.call(args)
        if rv:
            raise SystemError("raspistill exited with %d" % rv)
        return

    def take_still_picamera(self, outfile='/tmp/still.jpg',
                            res=[640, 480], format=None):
        '''Take a still photo using the Raspberry Pi camera module
           and the picamera Python module.
           Does not support outfile = '-'.
        '''
        if self.verbose:
            print("Res:", res)
            if res:
                res_str = "%dx%d" % tuple(res)
            else:
                res_str = "(unknown res)"
            print("Taking %s photo with picamera module" % res_str)

        with picamera.PiCamera(resolution=res) as camera:
            # camera.resolution = res
            camera.start_preview()
            # Camera warm-up time
            time.sleep(2)
            if outfile == '-':
                stream = io.BytesIO()
                camera.capture(stream, format='jpeg')
                # "Rewind" the stream to the beginning to read its contents
                stream.seek(0)
                return stream
            else:
                camera.capture(outfile)

            # Is this needed? What does previewing mean?
            camera.stop_preview()

    def take_video_picamera(self, outfile='/tmp/video.h264',
                   res=[640, 480], format=None):
        '''This routine is untested and probably broken.'''
        if self.verbose:
            print("Taking photo with picamera module")
        with self.camera as camera:
            camera.resolution = res
            camera.start_preview()
            # Camera warm-up time
            time.sleep(2)
            camera.brightness = 60
            camera.start_recording('video.h264')
            sleep(10)
            camera.stop_recording()

            # Is this needed? What does previewing mean?
            camera.stop_preview()

    def take_video_shell(self, outfile='/tmp/video.h264',
                   res=[640, 480], format=None):
        '''This routine is untested and probably broken.'''
        if not self.has_camera():
            raise SystemError("Can't find either a USB camera or a Pi camera!")

        if not os.path.exists('/usr/bin/raspivid'):
            raise SystemError("Neither python-picamera nor raspivid is installed")
        if self.verbose:
            print("Taking video with raspivid")
        rv = subprocess.call(['raspivid', '-o', filename,
                              '-t', '10000'])
        if rv:
            raise SystemError("raspivid exited with %d" % rv)
        return

if __name__ == '__main__':
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-v", "--verbose",
                         action="store_true", dest="verbose",
                         help="Verbose: chatter about what it's doing")
    optparser.add_option("-s", "--seconds", metavar="seconds",
                         action="store", dest="seconds",
                         help="Take video for s seconds, instead of a still")
    (options, args) = optparser.parse_args()

    print("Seconds:", options.seconds)

    if options.seconds:
        take_video(seconds=options.seconds, verbose=options.verbose)
    else:
        take_still(args[0], verbose=options.verbose)

