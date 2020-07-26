#!/usr/bin/env python3

# Use the astroalign module to align and stack a series of astro images.

# Based on https://share.cocalc.com/share/b66ffe0d5b2bc8ff75ac939486710731c2b030f6/astroalign-124/astroalign-py3.ipynb?viewer=share
# Note that the cocalc example is apparently based on a different
# version of astroalign from the one currently in pip,
# and doesn't expect the footprint second argument from register().

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


np.random.seed(seed=12)


def register_all(images, outdir=".", ext="png"):
    """Register a set of images (filenames) to the first image.
       Save each image (including the unchanged first one) as a
       set of png images with a_ prepended to the names.
       Input images may be filenames, or may already be numpy arrays.
    """
    baseimg = read_image(images[0])
    baselayer = singlelayer(baseimg)

    for i, img in enumerate(images):
        if i > 0:
            imgarr = read_image(img)
            aligned_img = register(imgarr, baselayer)
        else:
            # For the first image, don't align it, but do turn it
            # into a PIL image so it can be saved like the others.
            aligned_img = Image.fromarray(baseimg)

        print("Aligned image mode:", aligned_img.mode)

        print("shape", aligned_img.width, aligned_img.height)
        if type(img) is str:
            fname = os.path.splitext(os.path.basename(img))[0]
            outfname = f"a_{fname}.{ext}"
        else:
            outfname = f"a_img_{i}.{ext}"

        outfname = os.path.join(outdir, outfname)

        if aligned_img.mode != 'RGB':
            print("Converting monochrome image to save as PNG")
            aligned_img = aligned_img.convert("RGB")

        aligned_img.save(outfname)
        if os.path.exists(outfname):
            print("Overwriting", outfname)
        else:
            print("Creating", outfname)


# Multiple color layers? Use just the green layer for alignment.
def singlelayer(img, layer=1):
    if len(img.shape) == 3:
        return img[:, :, layer]
    return img


def register(rgbimage, baselayer):
    """Align an image of type numpy.ndarray to a base image.
       Input is normally an rgbimage, shape (width, height, 3)
       but can also be monochrome, (width, height, 1).
       Return the realigned image as an RGB PIL.Image.
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
    plot_three(baselayer, img2, img_aligned,
               pos_img=pos_img, pos_img_rot=pos_img_rot, transf=transf)

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

    return Image.fromarray(rgbArray)


def make_test_images():
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
    if 'rawpy' in sys.modules:
        try:
            with rawpy.imread(path) as raw:
                # raw.postprocess() -> numpy.ndarray of shape (2856, 4290, 3)
                # Use only the green channel.
                print("Reading", path, "as raw")
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
    parser.add_argument('imagefiles', nargs='*', help="2 or more input images")
    args = parser.parse_args(sys.argv[1:])

    if args.test:
        register_all(make_test_images(), outdir=args.dir)
        sys.exit(0)

    if len(args.imagefiles) < 2:
        parser.print_help()
        sys.exit(1)

    register_all(args.imagefiles, outdir=args.dir)
