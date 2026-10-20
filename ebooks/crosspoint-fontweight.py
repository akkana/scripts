#!/usr/bin/env python3

# Create Crosspoint (Xteink reader) fonts that are bolder than
# the commonly distributed fonts, starting from a TTF.

# Generates fonts of several bolder weights, and then convert them to
# crosspoint .cpfont files to use an a Xteink ebook reader.

# Make a link to crosspoint-reader/lib/EpdFont/scripts/fontconvert_sdcard.py
# somewhere in your path, then run giving it the path to the
# roman and italic TTF files. (Theoretically the italic file is optional,
# but that hasn't been tested yet.)

# Produces three directories representing bolder and less bold weights,
# each containing .cpfont files of four sizes.
# You can copy those directories directly onto /Fonts on the Xteink SD card.

import subprocess
import re
import sys, os


def gen_cpfont(familyname, roman_ttf, italic_ttf, weights, sizes='12,14,16,18'):
    created = []
    for weight in weights:
        boldweight = weight + 175
        # 800 is apparently the maximum weight
        if boldweight > 800:
            boldweight = 800
        files = [f"{familyname}-{weight}.ttf",
                 f"{familyname}-bold-{weight}.ttf",]
        if os.path.exists(files[0]):
            print(files[0], "already os.path.exists")
        else:
            print("Generating", files[0])
            subprocess.call(["fonttools", "varLib.instancer", roman_ttf,
                             f"wght={weight}",
                             "-o", files[0]])

        if os.path.exists(files[1]):
            print(files[1], "already os.path.exists")
        else:
            print("Generating", files[1])
            subprocess.call(["fonttools", "varLib.instancer", roman_ttf,
                             f"wght={boldweight}",
                             "-o", files[1]])
        args = ['fontconvert_sdcard.py',
                '--regular', files[0],
                '--bold', files[1]]

        if italic_ttf:
            files += [f"{familyname}-italic-{weight}.ttf",
                      f"{familyname}-italic-bold-{weight}.ttf"]
            if os.path.exists(files[2]):
                print(files[2], "already os.path.exists")
            else:
                print("Generating", files[2])
                subprocess.call(["fonttools", "varLib.instancer", italic_ttf,
                                 f"wght={weight}",
                                 "-o", files[2]])
            if os.path.exists(files[3]):
                print(files[3], "already os.path.exists")
            else:
                print("Generating", files[3])
                subprocess.call(["fonttools", "varLib.instancer", italic_ttf,
                                 f"wght={boldweight}",
                                 "-o", files[3]])

            args += [ '--italic', files[2],
                      '--bolditalic', files[3] ]

        familydir = f'{familyname}-{weight}'
        if not os.path.isdir(familydir):
            os.mkdir(familydir)
        created.append(familydir)
        args += [ '--intervals', 'latin-ext', '--sizes', sizes,
                  '--name', familydir,
                  '--output-dir', familydir ]

        print("======= Calling:", ' '.join(args))
        if subprocess.call(args):
            print("Error, exiting")
            sys.exit(1)
        print()

    print("Created:", ' '.join(created))


if __name__ == '__main__':
    try:
        roman_ttf = sys.argv[1]
        italic_ttf = sys.argv[2]
    except:
        print("Usage: %s roman.ttf [italic.ttf]" % sys.argv[0])
        print(f"For example, {sys.argv[0]} "
              "Bitter-VariableFont_wght.ttf "
              "Bitter-Italic-VariableFont_wght.ttf")
        sys.exit(1)
    familyname = re.split(r'[-\.]', roman_ttf)[0]
    midweight = 550
    weights = [ midweight + diff for  diff in [ -125, -75, 0, 75, 125] ]
    try:
        gen_cpfont(familyname, roman_ttf, italic_ttf, weights,
                   '12,13,14,15,16,17,18')
    except KeyboardInterrupt:
        pass

