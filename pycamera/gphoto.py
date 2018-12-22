#!/usr/bin/env python

from __future__ import print_function

import os, sys
import subprocess
import datetime

# There is something like a set of gphoto2 python bindings, at
# http://magiclantern.wikia.com/wiki/Remote_control_with_PTP_and_Python
# but it's not widely available and you'd have to compile it for the RPi.

camera_name = None

def has_camera():
    '''Is there a gphoto2-compatible camera installed?
       gphoto2 --auto-detect doesn't do anything helpful like,
       say, exiting with a different status if there's no camera.
       So we have to parse the output.
    '''
    try:
        output = subprocess.check_output(["/usr/bin/gphoto2",
                                          "--auto-detect"]).split('\n')
        seen_separator = False
        for line in output:
            if seen_separator:
                if len(line) > 1 and not line[0].isspace():
                    global camera_name
                    camera_name = line.strip()
                    return camera_name
            elif line.startswith("---------------"):
                seen_separator = True
        return False
    except:
        return False

class Gphoto :

    def __init__(self, res=None, verbose=False):
        '''May raise CalledProcessError or NotImplementedError
           if there's no compatible camera connected and switched on.
           XXX res is ignored for now.
        '''
        self.verbose = verbose

    def check_config(self):
        '''This routine tends to fail -- gphoto2 prints
           "** Error (-1: 'Unspecified error') ***" --
           even when the camera can capture just fine. So skip it.
        '''
        # Do we have a real camera attached using PTP so gphoto2 can talk to it?
        has_capture = False
        # For some reason gphoto2 --list-config ALWAYS exits with nonzero
        # and "*** Error (-1: 'Unspecified error') ***"
        # so alas we have to ignore error returns.
        # gphoto2 --set-config capture=1 --list-config is the right way.
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
        
    def take_still(self, outfile=None, res=None, zoom=None):
        if res:
            print("Warning: gphoto wrapper ignoring resolution", res)

        # gphoto2 can only take photos to files on the same filesystem
        # as the current working directory.
        print()
        # So if outfile points to another filesystem, we need to
        # change directory to that filesystem.
        if outfile and outfile != '-':
            if outfile[0] == '/':
                outdir = os.path.split(outfile)[0]
                if os.stat(outdir).st_dev != os.stat(os.getcwd()).st_dev:
                    if self.verbose:
                        print(outfile, "is not on the same filesystem as", \
                            os.getcwd())
                        print("Changing directory to", outdir)
                        os.chdir(outdir)
                        # XXX should we change back afterward?

            # gphoto2 will also prompt if the target file already exists,
            # so we have to rename or remove it.
            print("Checking whether", outfile, "exists already")
            if os.path.exists(outfile):
                if self.verbose:
                    print("Renaming", outfile, "to", outfile + ".bak")
                os.rename(outfile, outfile + ".bak")
        else:
            print("Not checking, outfile =", outfile)

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
    if not gphoto.has_camera():
        print("No camera connected!")
        sys.exit(0)
    gphoto.take_still()
    gphoto.take_still(zoom=10)
