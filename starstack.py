#!/usr/bin/env python3

# Use the astroalign module to align and stack a series of astro images.

# Based on https://share.cocalc.com/share/b66ffe0d5b2bc8ff75ac939486710731c2b030f6/astroalign-124/astroalign-py3.ipynb?viewer=share
# Note that the cocalc example is apparently based on a different
# version of astroalign from the one currently in pip,
# and doesn't expect the footprint second argument from register().

import astroalign
import numpy as np
import matplotlib.pyplot as plt
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

# Register the two images
# img_aligned = astroalign.register(img, img_rotated)
img_aligned, footprint = astroalign.register(img, img_rotated)

# Plot the results
fig, axes = plt.subplots(2, 2, figsize=(10, 10))
axes[0, 0].imshow(img, cmap='gray', interpolation='none', origin='lower')
axes[0, 0].axis('off')
axes[0, 0].set_title("Source Image")

axes[0, 1].imshow(img_rotated, cmap='gray', interpolation='none',
                  origin='lower')
axes[0, 1].axis('off')
axes[0, 1].set_title("Target Image")

print("img_aligned:", img_aligned[0])
axes[1, 1].imshow(img_aligned, cmap='gray', interpolation='none',
                  origin='lower')
axes[1, 1].axis('off')
axes[1, 1].set_title("Source Image aligned with Target")

axes[1, 0].axis('off')

plt.tight_layout()
plt.show()


# Print stats

transf, (pos_img, pos_img_rot) = astroalign.find_transform(img, img_rotated)

print("Rotation: {:.2f} degrees".format(transf.rotation * 180.0 / np.pi))
print("\nScale factor: {:.2f}".format(transf.scale))
print("\nTranslation: (x, y) = ({:.2f}, {:.2f})".format(*transf.translation))
print("\nTranformation matrix:\n{}".format(transf.params))
print("\nPoint correspondence:")
for (x1, y1), (x2, y2) in zip(pos_img, pos_img_rot):
    print("({:.2f}, {:.2f}) in source --> ({:.2f}, {:.2f}) in target"
          .format(x1, y1, x2, y2))


# Plot correspondences

fig, axes = plt.subplots(2, 2, figsize=(10, 10))

colors = ['r', 'g', 'b', 'y', 'cyan', 'w', 'm']

axes[0, 0].imshow(img, cmap='gray', interpolation='none', origin='lower')
axes[0, 0].axis('off')
axes[0, 0].set_title("Source Image")
for (xp, yp), c in zip(pos_img[:len(colors)], colors):
    circ = plt.Circle((xp, yp), 4, fill=False, edgecolor=c, linewidth=2)
    axes[0, 0].add_patch(circ)

axes[0, 1].imshow(img_rotated, cmap='gray', interpolation='none',
                  origin='lower')
axes[0, 1].axis('off')
axes[0, 1].set_title("Target Image")
for (xp, yp), c in zip(pos_img_rot[:len(colors)], colors):
    circ = plt.Circle((xp, yp), 4 * transf.scale, fill=False, edgecolor=c,
                      linewidth=2)
    axes[0, 1].add_patch(circ)

axes[1, 1].imshow(img_aligned, cmap='gray',
                  interpolation='none', origin='lower')
axes[1, 1].axis('off')
axes[1, 1].set_title("Source Image aligned with Target")
for (xp, yp), c in zip(pos_img_rot[:len(colors)], colors):
    circ = plt.Circle((xp, yp), 4 * transf.scale, fill=False, edgecolor=c,
                      linewidth=2)
    axes[1, 1].add_patch(circ)

axes[1, 0].axis('off')

plt.tight_layout()
plt.show()


# Align again
img_aligned2 = astroalign.apply_transform(transf, img, img_rotated)

fig, axes = plt.subplots(2, 2, figsize=(10, 10))
axes[0, 0].imshow(img, cmap='gray', interpolation='none', origin='lower')
axes[0, 0].axis('off')
axes[0, 0].set_title("Source Image")

axes[0, 1].imshow(img_rotated, cmap='gray', interpolation='none', origin='lower')
axes[0, 1].axis('off')
axes[0, 1].set_title("Target Image")

axes[1, 1].imshow(img_aligned2[0], cmap='gray', interpolation='none', origin='lower')
axes[1, 1].axis('off')
axes[1, 1].set_title("Source Image aligned with Target")

axes[1, 0].axis('off')

plt.tight_layout()
plt.show()


if __name__ == '__main__':
    pass

