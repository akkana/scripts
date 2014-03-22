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

import os
import subprocess
import time

def take_photo(outfile='/tmp/still.jpg', res=[640, 480]):
    # Do we have a USB camera for which we can use fswebcam?
    if os.path.exists('/dev/video0'):
        rv = subprocess.call(['/usr/bin/fswebcam', '-d', '/dev/video0',
                              '-r', '%dx%d' % tuple(res), outfile])
        if not rv:
            return
        print "fswebcam failed! Returned %d" % rv

    # No luck with a USB camera. Is there a Pi camera?
    if not os.path.exists('/dev/fb0'):
        raise SystemError, "Can't find either a USB camera or a Pi camera!"

    # Can we use the picamera module?
    try:
        import picamera
    except ImportError:
        # picamera isn't installed. Can we use raspistill?
        if not os.path.exists('/usr/bin/raspistill'):
            raise SystemError, \
                "Neither python-picamera nor raspistill is installed"
        rv = subprocess.call(['/usr/bin/raspistill', '-o', outfile])
        if rv:
            raise "raspistill exited with %d" % rv
        return

    with picamera.PiCamera() as camera:
        camera.resolution = res
        camera.start_preview()
        # Camera warm-up time
        time.sleep(2)
        camera.capture(outfile)

        # Is this needed? What does previewing mean?
        camera.stop_preview()

if __name__ == '__main__':
    take_photo()

