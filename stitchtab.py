#!/usr/bin/env python3

"""Stitch together a bunch of screenshots with a tab at a specified
   place, into a single tab image
"""

from PIL import Image
import os


def combine_images(fileprefix, bounds):
    """Combine all images in imgdir/fileprefix* after cropping to
       the given bounds (x0, y0, x1, y1).
       Files must be named {fileprefix}NNN.ext
       where NNN is an integer with any number of digits
       Save the result to imgdire/fileprefix-all.jpg.
    """
    imgdir, fileprefix = os.path.split(fileprefix)
    if not imgdir:
        imgdir = '.'
    files = []
    prefixlen = len(fileprefix)
    for f in os.listdir(imgdir):
        if f.startswith(fileprefix) and '-all' not in f:
            files.append(f)

    def sortkey(f):
        return int(os.path.splitext(f[prefixlen:])[0])
    files.sort(key=sortkey)

    cropheight = bounds[3] - bounds[1]
    destim = Image.new('RGB', (bounds[2] - bounds[0], cropheight * len(files)))

    for i, f in enumerate(files):
        print(f)
        im = Image.open(os.path.join(imgdir, f))

        im = im.crop(bounds)
        # im.show()
        destim.paste(im, (0, cropheight * i))

    destfile = os.path.join(imgdir, fileprefix + '-all.jpg')
    destim.save(destfile)
    print("Saved to", destfile)


if __name__ == '__main__':
    import sys

    def Usage():
        print("Usage:", os.path.basename(sys.argv[0]),
              "fileprefix x0 y0 x1 y1")
        sys.exit(1)

    if len(sys.argv) != 6:
        Usage()
    try:
        bounds = list(map(int, sys.argv[2:]))
    except Exception as e:
        print(e)
        Usage()

    combine_images(sys.argv[1], bounds) # (0, 126, 1920, 475))

