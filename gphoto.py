#!/usr/bin/env python

from __future__ import print_function

import os
import subprocess
import datetime

# There is something like a set of gphoto2 python bindings, at
# http://magiclantern.wikia.com/wiki/Remote_control_with_PTP_and_Python
# but it's not widely available and you'd have to compile it for the RPi.

class Gphoto :

    def __init__(self, verbose=False):
        """May raise CalledProcessError or NotImplementedError
           if there's no compatible camera connected and switched on.
        """
        self.verbose = verbose

    def check_config(self):
        """This routine tends to fail -- gphoto2 prints
           "** Error (-1: 'Unspecified error') ***" --
           even when the camera can capture just fine. So skip it.
        """
        # Do we have a real camera attached using PTP so gphoto2 can talk to it?
        has_capture = False
        # For some reason gphoto2 --list-config ALWAYS exits with nonzero
        # and "*** Error (-1: 'Unspecified error') ***"
        # so alas we have to ignore error returns.
        try:
            args = [ "/usr/bin/gphoto2",
                     # "--debug", "--debug-logfile=/tmp/log.txt",
                     "--list-config",
                     "capture=on"]
            config = subprocess.check_output(args)
        except subprocess.CalledProcessError as e:
            print("list-config exited with status", e.returncode)
            config = e.output
            print("output was: <START>", end=' ')
            print(config)
            print("<END>")
        for line in config.split('\n'):
            if line.startswith('/main/settings/capture'):
                has_capture = True
                break
            else: print(line, "isn't capture")
        if not has_capture:
            raise NotImplementedError

    def take_still(self, outfile=None, zoom=None):
        if not outfile:
            now = datetime.datetime.now()
            outfile = "snap-%04d-%02d-%02d-%02d-%02d-%02d.jpg" % \
                (now.year, now.month, now.day, now.hour, now.minute, now.second)
            # gphoto2 can handle date formatting, but in that case
            # we'd have no idea what the actual filename was
            # so we couldn't do anything with it later.
        print("outfile is now", outfile)

        args = [ "/usr/bin/gphoto2", "--set-config", "syncdatetime=1",
                 "--set-config", "capturetarget=sdram" ]
        if zoom:
            args.append("--set-config")
            args.append("zoom=%s" % str(zoom))

        # The capture image command and filename have to come last:
        args.append("--capture-image-and-download")
        args.append("--filename")
        args.append(outfile)

        if self.verbose:
            print("Calling:", args)

        rv = subprocess.call(args)

if __name__ == '__main__':
    gphoto = Gphoto(verbose=True)
    gphoto.take_still(zoom=1)
    gphoto.take_still(zoom=10)
