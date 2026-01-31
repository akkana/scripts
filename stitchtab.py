#!/usr/bin/env python3

"""Stitch together a bunch of screenshots with a tab at a specified
   place, into a single tab image
"""

from PIL import Image, ImageTk
import tkinter as tk
import os


def query_for_bounds(firstimg):
    window = tk.Tk()
    im = Image.open(firstimg)
    canvas = tk.Canvas(window, width=im.size[0], height=im.size[1])
    canvas.pack()
    image_tk = ImageTk.PhotoImage(im)
    canvas.create_image(im.size[0]//2, im.size[1]//2, image=image_tk)
    text = "Left click at upper left; right click at lower right"
    text_item = canvas.create_text(200, 200,
                                   fill="yellow", justify=tk.LEFT, anchor='nw',
                                   font=('sans', 30, 'bold'),
                                   text=text)
    bbox = canvas.bbox(text_item)
    rect_item = canvas.create_rectangle(bbox, outline="red", fill="black")
    canvas.tag_raise(text_item,rect_item)

    x0, y0, x1, y1 = None, None, None, None
    set_0, set_1 = False, False

    def callback(event):
        nonlocal x0, y0, x1, y1, set_0, set_1
        # print("clicked at:", event.x, event.y, "button", event.num)
        if event.num == 1:
            x0, y0 = event.x, event.y
            set_0 = True
        elif event.num == 3:
            x1, y1 = event.x, event.y
            set_1 = True

        if set_0 and set_1:
            window.destroy()

    canvas.bind("<Button-1>", callback)
    canvas.bind("<Button-3>", callback)

    window.mainloop()
    print("Bounds:", x0, y0, x1, y1)
    return (x0, y0, x1, y1)


def combine_images(fileprefix, outputfile=None, bounds=None, addspace=False):
    """Combine all images in imgdir/fileprefix* after cropping to
       the given bounds (x0, y0, x1, y1).
       If bounds are not specified, query for them.
       If lyricspace is True, leave a little space for lyrics
       between bars.
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

    if not bounds:
        bounds = query_for_bounds(os.path.join(imgdir, files[0]))

    cropheight = bounds[3] - bounds[1]
    if addspace:
        ymult = 1.15
    else:
        ymult = 1.0
    destim = Image.new('RGB', (bounds[2] - bounds[0],
                               int(cropheight * len(files) * ymult)))

    for i, f in enumerate(files):
        print(f)
        im = Image.open(os.path.join(imgdir, f))

        im = im.crop(bounds)
        # im.show()
        destim.paste(im, (0, int(cropheight * i * ymult)))

    if not outputfile:
        outputfile = os.path.join(imgdir, fileprefix + '-all.jpg')
    destim.save(outputfile)
    print("Saved to", outputfile)


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Combine images vertically")
    parser.add_argument('-s', "--space", dest="addspace", default=False,
                        action="store_true",
                        help="Add space for lyrics between images")
    parser.add_argument('-o', action="store", default=None, dest="outputfile",
                        help='Output filename')
    parser.add_argument('filepat',
                        help='file prefix, preceding number and extension')
    parser.add_argument('bounds', nargs='*', help="x0 y0 x1 y1")
    args = parser.parse_args(sys.argv[1:])
    print("args:", args)

    combine_images(args.filepat, args.outputfile,
                   bounds=list(map(int, args.bounds)),
                   addspace=args.addspace)

