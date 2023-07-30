#!/usr/bin/env python3

# Run mplayer on the given files, displaying each filename as a subtitle, as
# hinted at by https://wiki.multimedia.cx/index.php/MPlayer_FAQ#Subtitle/OSD


import subprocess
import os, sys


def create_subtitle_file(filename):
    filename = os.path.basename(filename)
    filebase, ext = os.path.splitext(filename)
    subfilename = "/tmp/subtitles%s.srt" % filebase
    if os.path.exists(subfilename):
        return subfilename
    with open(subfilename, "w") as subfp:
        print("1\n00:00:00,0 --> 01:00:00,0\n%s" % filename, file=subfp)
    return subfilename


if __name__ == '__main__':
    args = [ "mplayer" ]
    for filename in sys.argv[1:]:
        args.append(filename)
        args.append("-sub")
        args.append(create_subtitle_file(filename))

    subprocess.run(args)

