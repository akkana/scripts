#!/usr/bin/env python3

import sys
import subprocess

# Copy a file, suitably downsized, to the clipboard in PNG format
# so it can be pasted by an app like Discord.

# Usage: imgcpy foo.jpg [new-pixel-width]

# From the commandline:
#   convert $img png:- | xclip -selection clipboard -target image/png
# but this script also resizes if the file is large.

# To verify this worked:
# Show type available: xclip -selection clipboard -t TARGETS -o
# Get it: xclip -selection clipboard -t image/png -o > /tmp/img.png


# Images can be a little over the given size without being rescaled
SLOP = 1.3


def copy_to_clip(imgfile, maxwidth):
    ident = subprocess.check_output(['identify', imgfile])
    width, height = ident.split()[2].split(b'x')
    args = ['convert', imgfile]

    if width >= height:
        if int(width) > maxwidth*SLOP:
            print("Rescaling (landscape)")
            args.append('-scale')
            args.append('%dx' % maxwidth)
    else:
        if int(height) > maxwidth*SLOP:
            print("Rescaling (portrait)")
            args.append('-scale')
            args.append('x%d' % maxwidth)

    args.append('png:-')
    pngbits = subprocess.check_output(args)

    subprocess.run(['xclip', '-selection', 'clipboard',
                    '-target', 'image/png'],
                   input=pngbits)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: imgcpy foo.jpg [approx-max-dimension]")
        sys.exit(1)

    img = sys.argv[1]

    width = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    copy_to_clip(img, width)



