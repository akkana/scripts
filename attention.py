#!/usr/bin/env python3

"""Attention vs Distraction:
   keep a record of workspace switching and keyboard use.
   Inspired by Gloria Mark's work discussed ont he Hidden Brain podcast episode
   https://hiddenbrain.org/podcast/finding-focus/
"""

from os.path import expanduser, join, exists

DATADIR = join(expanduser("~/Data/attention"))


import time
import subprocess


SLEEPSECS = 30


def wakeup():
    idlesec = getIdleSec()
    workspaces, active = get_workspaces()

    datafile = join(DATADIR, time.strftime("%Y-%m-%d") + ".csv")
    if not exists(datafile):
        with open(datafile, 'w') as ofp:
            print("time,idlesec,desktopnum,desktopname", file=ofp)

    with open(datafile, 'a') as ofp:
        print("%s,%d,%d,%s" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                               idlesec, active, workspaces[active]),
              file=ofp)


# wmctrl -d can show which desktop is active
# wmctrl -l -G shows windows on all desktops

def get_workspaces():
    """Use wmctrl to get a list of all virtual desktops.
       Return a dict of workspaces, and the number of the active one.
    """
    workspaces = {}
    active = None
    proc = subprocess.run(["wmctrl", "-d"], capture_output=True)
    for line in proc.stdout.splitlines():
        words = line.split()
        num = int(words[0])

        # Just in case it's possible to have a space in the workspace name
        workspaces[num] = b' '.join(words[9:]).decode()
        if words[1] == b'*':
            active = num

    return workspaces, active


# May eventually want to look at active windows, see if we're
# googling in firefox, etc.
# def get_windows():
#     """Use wmctrl to figure out which desktop we're on"""
#     proc = subprocess.run(["wmctrl", "-l", "-G"], capture_output=True)
#     for line in proc.stdout.splitlines():
#         if not line.endswith(b'irefox'):
#             continue


###################################################################
# Discussion of methods of getting idle time:

# Getting idle time is harder. For an example of how frustrating it can be,
# see discussion at
# https://github.com/Zygo/xscreensaver/blob/0c43268adc2e7a932ca5427db7b18d37ef53f7ad/driver/xscreensaver.c#L119
# and continue reading at line 1848.

# Installing xprintidle would work; xprintidle itself uses the
# Xlib scrnsaver extension, which in Python is from Xlib.ext import screensaver
# but attempting to screensaver.QueryInfo(dpy, root) fails with
# Missing required argument opcode. No opcode is needed in the C code),
# so I can only guess that this is a bug in the Python port of the extension.

# But the best method I've found that doesn't require installing any
# additional programs is this one, from gajim
# https://dev.gajim.org/gajim/gajim/-/blob/master/gajim/common/idle.py
# which is adapted here:

import ctypes
import ctypes.util

class XScreenSaverInfo(ctypes.Structure):
    _fields_ = [
            ('window', ctypes.c_ulong),
            ('state', ctypes.c_int),
            ('kind', ctypes.c_int),
            ('til_or_since', ctypes.c_ulong),
            ('idle', ctypes.c_ulong),
            ('eventMask', ctypes.c_ulong)
    ]
XScreenSaverInfo_p = ctypes.POINTER(XScreenSaverInfo)

display_p = ctypes.c_void_p
xid = ctypes.c_ulong
c_int_p = ctypes.POINTER(ctypes.c_int)

try:
    libX11path = ctypes.util.find_library('X11')
    if libX11path is None:
        raise OSError('libX11 could not be found.')
    libX11 = ctypes.cdll.LoadLibrary(libX11path)
    libX11.XOpenDisplay.restype = display_p
    libX11.XOpenDisplay.argtypes = ctypes.c_char_p,
    libX11.XDefaultRootWindow.restype = xid
    libX11.XDefaultRootWindow.argtypes = display_p,

    libXsspath = ctypes.util.find_library('Xss')
    if libXsspath is None:
        raise OSError('libXss could not be found.')
    libXss = ctypes.cdll.LoadLibrary(libXsspath)
    libXss.XScreenSaverQueryExtension.argtypes = display_p, c_int_p, c_int_p
    libXss.XScreenSaverAllocInfo.restype = XScreenSaverInfo_p
    libXss.XScreenSaverQueryInfo.argtypes = (display_p, xid, XScreenSaverInfo_p)

    dpy_p = libX11.XOpenDisplay(None)
    if dpy_p is None:
        raise OSError('Could not open X Display.')

    _event_basep = ctypes.c_int()
    _error_basep = ctypes.c_int()
    if libXss.XScreenSaverQueryExtension(dpy_p, ctypes.byref(_event_basep),
                    ctypes.byref(_error_basep)) == 0:
        raise OSError('XScreenSaver Extension not available on display.')

    xss_info_p = libXss.XScreenSaverAllocInfo()
    if xss_info_p is None:
        raise OSError('XScreenSaverAllocInfo: Out of Memory.')

    rootwindow = libX11.XDefaultRootWindow(dpy_p)
    xss_available = True
except OSError:
    # Logging?
    xss_available = False

def getIdleSec():
    global xss_available
    """
    Return the idle time in seconds
    """
    if not xss_available:
        return -1
    if libXss.XScreenSaverQueryInfo(dpy_p, rootwindow, xss_info_p) == 0:
        return -1
    else:
        return int(xss_info_p.contents.idle) / 1000

def close_xss():
    global xss_available
    if xss_available:
        libX11.XFree(xss_info_p)
        libX11.XCloseDisplay(dpy_p)
        xss_available = False

# end idle time code
###################################################################


if __name__ == '__main__':
    while True:
        wakeup()
        time.sleep(SLEEPSECS)
