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

import os, sys
import subprocess
import time
import StringIO

def take_still_or_video(still=True, outfile='/tmp/still.jpg',
                        res=[640, 480], seconds=10, verbose=False):
    '''Take either a still photo or a video.
       outfile can be specified as '-', in which case we will return
       a StringIO object containing the image data in memory
       which you can pass to PIL.Image.open().
       Don't forget to close it after opening the image!
    '''
    # Do we have a USB camera for which we can use fswebcam?
    if os.path.exists('/dev/video0'):
        if verbose:
            print "Taking photo with fswebcam ..."

        if still:
            args = ['/usr/bin/fswebcam', '-q', '--no-banner']
                    # '-d', '/dev/video0',
            if res:
                args.append('-r')
                args.append('%dx%d' % tuple(res))
            if outfile == '-':
                args.append('--png')
                args.append('5')
                    # the png compression level makes almost no difference
                args.append(outfile)
                if verbose:
                    print "Calling check_output", args
                image_data = StringIO.StringIO()
                image_data.write(subprocess.check_output(args))
                image_data.seek(0)
                return image_data
            else:
                args.append(outfile)
                if verbose:
                    print "Calling", args
                rv = subprocess.call(args)
        else:
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
                if verbose:
                    print outfile, "already exists. Removing it!"
                os.unlink(outfile)

            args = ['avconv', '-f', 'video4linux2', '-i', '/dev/video0',
                       '-s', '%dx%d' % tuple(res), '-t', str(seconds),
                       outfile]
            if verbose:
                print args
            rv = subprocess.call(args)


        if not rv:
            return

        if still:
            print "fswebcam failed! Error code %d" % rv
        else:
            print "avconv failed! Error code %d" % rv

    # No luck with a USB camera. Is there a Pi camera?
    if not os.path.exists('/dev/fb0'):
        raise SystemError, "Can't find either a USB camera or a Pi camera!"

    # Can we use the picamera module?
    try:
        import picameraXXX
        # temporarily not using picamera until we know how to
        # take a picture in memory
    except ImportError:
        if still:
            # picamera isn't installed. Can we use raspistill?
            if not os.path.exists('/usr/bin/raspistill'):
                raise SystemError, \
                    "Neither python-picamera nor raspistill is installed"
            if verbose:
                print "Taking photo with raspistill"
            args = ['/usr/bin/raspistill', '-o', outfile]
            if res:
                args.append('-w')
                args.append(str(res[0]))
                args.append('-h')
                args.append(str(res[1]))
            # Was hoping that increasing sharpness would help focus, but no.
            # if not res or res[1] >= 1600:
            #     args.append('-sh')
            #     args.append('100')
            print "Calling:", args
                    
            # If the outfile is specified as -, we want raw data.
            # PIL expects bmp data, apparently.
            if outfile == '-':
                args.append('-e')
                args.append('bmp')   # should compare png performance

                image_data = StringIO.StringIO()
                image_data.write(subprocess.check_output(args))
                image_data.seek(0)
                return image_data
            else:
                rv = subprocess.call(args)
            if rv:
                raise SystemError, "raspistill exited with %d" % rv
            return
        else:
            if not os.path.exists('/usr/bin/raspivid'):
                raise SystemError, \
                    "Neither python-picamera nor raspivid is installed"
            if verbose:
                print "Taking video with raspivid"
            rv = subprocess.call(['raspivid', '-o', filename, '-t', '10000'])
            if rv:
                raise SystemError, "raspivid exited with %d" % rv
            return

    if verbose:
        print "Taking photo with picamera"
    with picamera.PiCamera() as camera:
        camera.resolution = res
        camera.start_preview()
        # Camera warm-up time
        time.sleep(2)
        if still:
            camera.capture(outfile)
        else:
            camera.brightness = 60
            camera.start_recording('video.h264')
            sleep(10)
            camera.stop_recording()

        # Is this needed? What does previewing mean?
        camera.stop_preview()

def take_still(outfile='/tmp/still.jpg', res=[640, 480], verbose=False):
    return take_still_or_video(True, outfile, res=res, verbose=verbose)

def take_video(outfile='/tmp/video.mpg', res=[320, 240], seconds=10,
               verbose=False):
    return take_still_or_video(False, outfile, res=res, seconds=seconds,
                               verbose=verbose)

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

    print "Seconds:", options.seconds

    if options.seconds:
        take_video(seconds=options.seconds, verbose=options.verbose)
    else:
        take_still('-', verbose=options.verbose)

