#!/usr/bin/env python

# Copyright 2014 by Akkana Peck: share and enjoy under the GPL v2 or later.

'''picamera: find and use cameras of various types.

   A pycamera object will have the following methods:
   __init__(verbose)    # Set verbose to True for chatter on stdout
   take_still(outfile=None)
                        # If outfile is not specified, a name will be
                        # assigned that incorporates the data and time.
                        # take_still's other arguments will vary
                        # with the capability of the camera library.

    There may also be other routines, like take_video().
'''

__version__ = "0.1"
__author__ = "Akkana Peck <akkana@shallowsky.com>"
__license__ = "GPL v2"
__all__ = [ 'gphoto', "webcam", "piphoto" ]

# from . import *

import os

def has_webcamera():
    return os.path.exists('/dev/video0')

def has_picamera():
    # Regular Linux machines may have /dev/fb0,
    # but the Pi doesn't seem to have it unless a pi cam is connected.
    return os.uname()[4].startswith("arm") and os.path.exists('/dev/fb0')

from . import gphoto
def has_gphoto_camera():
    return gphoto.has_camera()

def find_cameras(verbose=False):
    '''Find the cameras connected to this machine, and return them
       in order of quality. That means
       try gphoto2 first, then webcam, then Pi camera.
    '''

    cameras = []

    if has_gphoto_camera():
        cameras.append(gphoto.Gphoto(verbose=verbose))

    if has_webcamera():
        from . import webcam
        cameras.append(webcam.WebCam(verbose=verbose))

    if has_picamera():
        from . import piphoto
        cameras.append(piphoto.PiCamera(verbose=verbose))

    return cameras
