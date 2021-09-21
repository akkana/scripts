#!/usr/bin/env python3

# This is a simple script that prints out the layers in a GIMP XCF file.
# Started from
# https://www.gimp-forum.net/Thread-List-layers-without-loading-image?pid=21911#pid21911
# then expanded after looking at the GIMP XCF code:
# https://gitlab.gnome.org/GNOME/gimp/-/blob/gimp-2-10/app/xcf/xcf-load.c#L1147
# https://gitlab.gnome.org/GNOME/gimp/-/blob/gimp-2-10/app/xcf/xcf-private.h
# which you'll need if you want to expand this beyond just layer names
# and visibility.
#
# This is a simple demo that only works with some XCF versions.

import sys

# The layer property types needed to show visibility and which layer is active:
PROP_END          = 0
PROP_ACTIVE_LAYER = 2
PROP_VISIBLE      = 8


def probe_xcf(filename):
    # open the file in readonly binary mode
    with open(filename, 'rb') as f:
        print("\n===", filename)

        # go to the 30th byte
        f.seek(30, 0)

        # read image properties
        while True:
            prop_type = int.from_bytes(f.read(4), "big")
            prop_size = int.from_bytes(f.read(4), "big")

            f.read(prop_size)

            if prop_type == PROP_END:
                break

        # read layers
        while True:
            next_layer_offset = int.from_bytes(f.read(8), "big")

            if not next_layer_offset: # end of layers offsets
                break;

            saved_pos = f.tell()
            f.seek(next_layer_offset + 12, 0)

            tmp = int.from_bytes(f.read(4), "big")
            name = f.read(tmp).decode("utf-8")
            print('\nLayer "%s"' % name, end='')

            while True:
                prop_type = int.from_bytes(f.read(4), "big")
                prop_size = int(int.from_bytes(f.read(4), "big") / 4)
                # print(prop_type, "size", prop_size)

                # The size says how many additional bytes need to be read.
                # Read them now, saving only the last one.
                for i in range(prop_size):
                    lastint = int.from_bytes(f.read(4), "big")

                if prop_type == PROP_VISIBLE:
                    if lastint:
                        print(" Visible", end='')
                    else:
                        print(" Invisible", end='')
                    break

                elif prop_type == PROP_ACTIVE_LAYER:
                    print(" Active", end='')

            f.seek(saved_pos, 0)

        print()


if __name__ == "__main__":
    for f in sys.argv[1:]:
        probe_xcf(f)

