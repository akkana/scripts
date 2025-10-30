#!/usr/bin/env python3

# Find images waiting in the queue to be turned into wallpaper.
# I.E.: Find files in ~/Images/Backgrounds/orig
# and images tagged 'wallpaper' in any directory arguments
# that don't yet exist in any directory ~/Backgrounds/1920xNNNN

from sys import argv, exit
from os import listdir, walk
from os.path import basename, expanduser, join, exists, isdir

from metapho import Tagger, imagelist


BGDIR = expanduser("~/Images/Backgrounds")

DOWNLOAD_DIR = join(BGDIR, "orig")

TARGET_DIRS = [ join(BGDIR, targ) for targ in listdir(BGDIR)
                if targ[:2] == '19' ]
WALLTAGS = [ "wallpaper", "background" ]


done = []
not_done = []

# Add subdirs of each target
add_dirs = []
for t in TARGET_DIRS:
    for root, dirs, files in walk(t):
        add_dirs.append(root)

TARGET_DIRS += add_dirs
# print("Target dirs:")
# for t in TARGET_DIRS:
#     print(t)


DONE_DIRS = [ join(DOWNLOAD_DIR, 'done'), join(DOWNLOAD_DIR, 'mine') ]


def already_done(bname):
    """Has the basename bname already been converted to wallpaper
       in one of the target directories?
    """
    for targ in TARGET_DIRS:
        if exists(join(targ, bname)):
            return True
    return False


# Step 1: look for files tagged wallpaper if any image directories
# were provided.
if len(argv) > 1:
    tagged_images = []
    for idir in argv[1:]:
        tagger = Tagger()
        tagger.read_tags(idir)
        imagelist_iter = imagelist.ImageListIterator()
        for im in iter(imagelist_iter):
            for walltag in WALLTAGS:
                for tagindex in im.tags:
                    if walltag == tagger.tag_list[tagindex] \
                       and im not in tagged_images:
                        tagged_images.append(im)
                        break

    # Now there's a good list of tagged_images.
    for im in tagged_images:
        bname = basename(im.filename)
        if already_done(bname):
            done.append(im.relpath)
            continue
        not_done.append(im.relpath)

    # If directories were passed in as arguments,
    # don't bother looking in standard dirs.

else:
    # Step 2: look for downloaded files in DOWNLOAD_DIR
    for root, dirs, files in walk(DOWNLOAD_DIR):
        if isdir(root) and root in DONE_DIRS:
            # print("Skipping", root)
            continue

        for bname in files:
            if not already_done(bname):
                not_done.append(bname)
            else:
                done.append(bname)

if done:
    print("Already done:", ' '.join(done))

for bname in not_done:
    print(bname)
