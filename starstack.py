#!/usr/bin/env python3

# Use the astroalign module to align and stack a series of astro images.

# Suggested Workflow;
# If starting with raw images, process them in darktable:
# - darktable *.cr2 (including dark frame, probably)
#   or if that doesn't work (darktable tends to freeze if you start it
#   with a list of images), use import/folder... in the lighttable tab.
# - lighttable tab: choose the first image
# - darkroom tab: fiddle with it until it looks like what you want
# - Ctrl-C (this copies the operation history, not the image)
# - lighttable tab: Click on each other image in turn and Ctrl-V
# - lighttable tab: export selected
# This will (by default) export to files under darktable_exported/
#
# You can run this script directly on the raw images, but the import
# with rawpy is one of two extremes: by default it does an extreme
# brightness auto-stretch, which leads to incredibly noisy astro images;
# or with no_auto_bright=True, you get no brightness improvement, so you
# lose a lot of the extra info stored in the raw file.
#
# The output of this script is a sequence of aligned images.
# astroalign doesn't do a perfect job (though it's quite a bit better
# than Siril), so I recommend loading the image(s) into GIMP
# and adjusting the alignment to your liking. Then set all the
# layer modes except the bottom one to Addition (or for fun, you
# might want to try Screen, Pin light, Luminance, or one of the LCh *)

# Copyright 2020 by Akkana Peck: Share and enjoy under the GPLv2 or later.
#
# Originally based on
# https://share.cocalc.com/share/b66ffe0d5b2bc8ff75ac939486710731c2b030f6/astroalign-124/astroalign-py3.ipynb?viewer=share
# (apparently based on an earlier version of astroalign).


import astroalign
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import argparse
import sys, os

# rawpy is optional. PIL can read some raw images (at least Canon cr2),
# but may not get the same results as rawpy does.
try:
    import rawpy
except:
    pass

# If the tifffile module is installed and the image extension is .tif
# save multi-page TIFFs that GIMP can open as layers,
# instead of separate images.
try:
    import tifffile
except:
    print("Can't import tifffile")
    pass


def register_all(images, outdir=".", ext="tif"):
    """Register a set of images (filenames) to the first image.
       Save each image (including the unchanged first one) as a
       set of png images with a_ prepended to the names.
       Input images may be filenames, or may already be numpy arrays.
    """
    baseimg = read_image(images[0])
    baselayer = singlelayer(baseimg)

    if ext.startswith('.'):
        ext = ext[1:]

    if ext.lower() == "tif" and 'tifffile' in sys.modules:
        tiff_multipage = os.path.join(outdir, "layers.tif")
    else:
        tiff_multipage = None

    for i, img in enumerate(images):
        if i > 0:
            imgarr = read_image(img)
            aligned_arr = register(imgarr, baselayer)
            aligned_img = Image.fromarray(aligned_arr)
        else:
            # For the first image, don't align it, but do turn it
            # into a PIL image so it can be saved like the others.
            aligned_arr = baseimg
            aligned_img = Image.fromarray(baseimg)

        if aligned_img.mode != 'RGB':
            print("Converting monochrome image to save as PNG")
            aligned_img = aligned_img.convert("RGB")

        if tiff_multipage:
            if type(img) is str:
                print("Adding", os.path.basename(img), "to", tiff_multipage)
            else:
                print("Adding layer", i, "to", tiff_multipage)
            tifffile.imwrite(tiff_multipage, aligned_arr, append=True)

        else:
            if type(img) is str:
                fname = os.path.splitext(os.path.basename(img))[0]
                outfname = f"a_{fname}.{ext}"
            else:
                outfname = f"a_img_{i}.{ext}"

            outfname = os.path.join(outdir, outfname)

            if os.path.exists(outfname):
                print("Overwriting", outfname)
            else:
                print("Creating", outfname)
            aligned_img.save(outfname)


# Multiple color layers? Use just the green layer for alignment.
def singlelayer(img, layer=1):
    if len(img.shape) >= 3:
        return img[:, :, layer]
    return img


def register(rgbimage, baselayer):
    """Align an image of type numpy.ndarray to a base image.
       Input is normally an rgbimage, shape (width, height, 3)
       but can also be monochrome, (width, height, 1).
       Return the realigned image as a numpy.ndarray.
    """
    img2 = singlelayer(rgbimage)

    # Register the two images
    img_aligned, footprint = astroalign.register(baselayer, img2)

    # Plot the results
    # plot_three(baselayer, img2, img_aligned)

    transf, (pos_img, pos_img_rot) = astroalign.find_transform(baselayer, img2)

    def print_stats():
        print("Rotation: %2d degrees" % (transf.rotation * 180.0 / np.pi))
        print("\nScale factor: %.2f" % transf.scale)
        print("\nTranslation: (x, y) = (%.2f, %.2f)"
              % tuple(transf.translation))
        print("\nTranformation matrix:\n", transf.params)
        print("\nPoint correspondence:")
        for (x1, y1), (x2, y2) in zip(pos_img, pos_img_rot):
            print("(%.2f, %.2f) in source --> (%.2f, %.2f) in target"
                  % (x1, y1, x2, y2))
    # print_stats()

    # Plot correspondences
    # plot_three(baselayer, img2, img_aligned,
    #            pos_img=pos_img, pos_img_rot=pos_img_rot, transf=transf)

    # Align again using the transform.
    # Will use this to align the other channels after using one
    # channel to register the two images.
    # The documentation doesn't mention a footprint being part of the return,
    # but it is.
    # realigned, footprint = astroalign.apply_transform(transf, baselayer, img2)

    # plot_three(baselayer, img2, realigned)

    newshape = rgbimage.shape
    if len(newshape) == 2:
        newshape = rgbimage.shape + (3,)

    # trying https://stackoverflow.com/a/10445502
    rgbArray = np.zeros(newshape, 'uint8')
    for i in range(newshape[-1]):
        layer = singlelayer(rgbimage, i)
        realigned, footprint = astroalign.apply_transform(transf, baselayer,
                                                          layer)

        rgbArray[..., i] = layer

    return rgbArray


def make_test_images():
    np.random.seed(seed=12)

    h, w = img_shape = (200, 200)
    n_stars = 10
    pos_x = np.random.randint(10, w - 10, n_stars)
    pos_y = np.random.randint(10, h - 10, n_stars)
    fluxes = 200.0 + np.random.rand(n_stars) * 300.0

    img = np.zeros(img_shape)
    for x, y, f in zip(pos_x, pos_y, fluxes):
        img[x, y] = f

    # Generate a test image that's rotated and noisy:

    # rotate and make the image one and a half times as big
    from scipy.ndimage import rotate, zoom
    img_rotated = rotate(img, angle=30.0, reshape=False)
    img_rotated = zoom(img_rotated, 1.5, order=2)

    # add a Gaussian PSF response with different seeing for both images
    from scipy.ndimage.filters import gaussian_filter
    img = gaussian_filter(img, sigma=2.0, mode='constant')
    img_rotated = gaussian_filter(img_rotated, sigma=1.5, mode='constant')

    # add some noise
    noise_dc = 5.0
    noise_std = np.sqrt(noise_dc)
    img += np.random.normal(loc=noise_dc, scale=noise_std, size=img.shape)
    img_rotated += np.random.normal(loc=noise_dc, scale=noise_std,
                                    size=img_rotated.shape)

    return img, img_rotated


def read_image(path):
    """If path is a filename, read an image from it into a numpy array.
       If it's already a numpy array, just return it.
    """
    if type(path) is np.ndarray:
        return path
    if type(path) is not str and type(path) is not bytes:
        raise RuntimeError("read_image can't process type " + str(type(path)))

    # First try reading as raw, if rawpy is loaded.
    # rawpy doesn't do a very good job by default, though.
    # Probably it would need some adjustment of parameters below.
    if 'rawpy' in sys.modules:
        try:
            with rawpy.imread(path) as raw:
                # raw.postprocess() -> numpy.ndarray of shape (2856, 4290, 3)
                # Use only the green channel.
                print("Reading", path, "as raw")

                # Relevant parameters:
                # https://letmaik.github.io/rawpy/api/rawpy.Params.html#rawpy.Params
                # no_auto_bright=True
                # auto_bright_thr=(float): ratio of clipped pixels with auto_bright. Default is 0.01 (1%).
                # bright (float) – brightness scaling
                # exp_shift (float) – exposure shift in linear scale. Usable range from 0.25 (2-stop darken) to 8.0 (3-stop lighter).
                # exp_preserve_highlights (float) – preserve highlights when lightening the image with exp_shift. From 0.0 to 1.0 (full preservation).
                # gamma (tuple) – pair (power,slope), default is (2.222, 4.5) for rec. BT.709
                return raw.postprocess()
        except rawpy._rawpy.LibRawFileUnsupportedError:
            pass

    image = Image.open(path)
    print("Reading", path, "with PIL")
    return np.asarray(image)


colors = ['r', 'g', 'b', 'y', 'cyan', 'w', 'm']

def plot_three(img1, img2, img3, labels=None,
               pos_img=None, pos_img_rot=None, transf=None):

    DEFLABELS = ["Target Image", "Target Image",
                 "Source Image aligned with Target"]

    def smalldim(im):
        return min(im.shape)

    if not labels:
        labels = DEFLABELS

    fig, axes = plt.subplots(2, 2, figsize=(10, 10))
    axes[0, 0].imshow(img1, cmap='gray', interpolation='none', origin='lower')
    axes[0, 0].axis('off')
    axes[0, 0].set_title(labels[0])
    if pos_img is not None:
        circsize = smalldim(img1) / 100
        for (xp, yp), c in zip(pos_img[:len(colors)], colors):
            circ = plt.Circle((xp, yp), circsize,
                              fill=False, edgecolor=c, linewidth=2)
            axes[0, 0].add_patch(circ)

    axes[0, 1].imshow(img2, cmap='gray', interpolation='none',
                      origin='lower')
    axes[0, 1].axis('off')
    axes[0, 1].set_title(labels[1])
    if transf and pos_img_rot is not None:
        circsize = smalldim(img2) / 100
        for (xp, yp), c in zip(pos_img_rot[:len(colors)], colors):
            circ = plt.Circle((xp, yp), circsize * transf.scale,
                              fill=False, edgecolor=c,
                              linewidth=2)
            axes[0, 1].add_patch(circ)

    axes[1, 1].imshow(img3, cmap='gray', interpolation='none',
                      origin='lower')
    axes[1, 1].axis('off')
    axes[1, 1].set_title(labels[2])
    if transf and pos_img_rot is not None:
        circsize = smalldim(img3) / 100
        for (xp, yp), c in zip(pos_img_rot[:len(colors)], colors):
            circ = plt.Circle((xp, yp), circsize * transf.scale,
                              fill=False, edgecolor=c,
                              linewidth=2)
            axes[1, 1].add_patch(circ)

    axes[1, 0].axis('off')

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stack astronomical images")
    parser.add_argument('-t', "--test", dest="test", default=False,
                        action="store_true",
                help="Test mode: generate images instead of reading files")
    parser.add_argument('-d', action="store", default='.', dest="dir",
                        help='Directory to save files (default: .)')
    parser.add_argument('-e', action="store", default='tif', dest="ext",
                        help='Output image file extension (default: tif)')
    parser.add_argument('imagefiles', nargs='*', help="2 or more input images")
    args = parser.parse_args(sys.argv[1:])

    if args.test:
        register_all(make_test_images(), outdir=args.dir, ext=args.ext)
        sys.exit(0)

    if len(args.imagefiles) < 2:
        parser.print_help()
        sys.exit(1)

    register_all(args.imagefiles, outdir=args.dir, ext=args.ext)
