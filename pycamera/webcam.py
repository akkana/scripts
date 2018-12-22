#!/usr/bin/env python

# Take photos or video with a USB webcam using fswebcam.

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

from __future__ import print_function

class WebCam:

    def __init__(self, verbose=False):
        self.verbose = verbose

    def take_still(self, outfile='/tmp/still.jpg',
                   res=[640, 480], format=None):
        '''Take a still photo.
           outfile can be specified as '-', in which case we will return
           a StringIO object containing the image data in memory
           which you can pass to PIL.Image.open().
           You may want to specify format= when using outfile='-'.
           Don't forget to close it after opening the image!
           Unspecified res means try to use the full resolution of the camera.
        '''
        # Do we have a USB camera for which we can use fswebcam?
        if not self.has_camera():
            raise SystemError("Can't find either a USB camera or a Pi camera!")

        if self.verbose:
            print("Taking photo with fswebcam ...")

        if format:
            format = format.lower()

        args = [ '/usr/bin/fswebcam', '-q', '--no-banner' ]
                # '-d', '/dev/video0',
        if res:
            args.append('-r')
            args.append('%dx%d' % tuple(res))
        else:
            # fswebcam defaults to 352 x 288 (??) and has no "full-res"
            # option, but passing a huge resolution seems to make it
            # fall back to the camera's maximum native resolution
            args.append('-r')
            args.append('3648x2736')

        if outfile == '-':
            if format == 'jpeg' or format == 'jpg':
                args.append('--jpeg')
                args.append('85')
            else:
                if format != 'PNG':
                    "Can't handle format", format, "-- defaulting to PNG"
                args.append('--png')
                args.append('5')
                # the png compression level makes almost no difference
            args.append(outfile)
            if self.verbose:
                print("Calling check_output", args)
            image_data = StringIO.StringIO()
            image_data.write(subprocess.check_output(args))
            image_data.seek(0)
            return image_data
        else:
            args.append(outfile)
            if self.verbose:
                print("Calling", args)
            rv = subprocess.call(args)

        print("fswebcam failed! Error code %d" % rv)

    def take_video(still=True, outfile='/tmp/still.jpg',
                            seconds=10, format=None):
        # Rupa's pidoorbell_recognizer used:
        # rv = call(['ffmpeg', '-f', 'video4linux2', '-s',
        #            '%dx%d' % tuple(res), '-i', '/dev/video0',
        #            '-f', 'alsa', '-ar', '22050', '-ac', '1',
        #            '-i', 'hw:1,0', '-ab', '48k', '-timelimit', '10',
        #            outfile])
        # but debian tells me ffmpeg is deprecated and I should use avconv.
        # Unfortunately, avconv seems to have no non-interactive option
        # to disable prompting if there's a file to be overwritten,
        # so check whether the target file already exists.
        if os.path.exists(outfile):
            if self.verbose:
                print(outfile, "already exists. Removing it!")
            os.unlink(outfile)

        args = ['avconv', '-f', 'video4linux2', '-i', '/dev/video0',
                   '-s', '%dx%d' % tuple(res), '-t', str(seconds),
                   outfile]
        if self.verbose:
            print(args)
        rv = subprocess.call(args)


        if not rv:
            return

        print("avconv failed! Error code %d" % rv)


