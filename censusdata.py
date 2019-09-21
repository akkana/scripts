#!/usr/bin/env python3

# Download Census data files for the 2000 Decadal Summary File 1:
# https://www2.census.gov/census_2000/datasets/Summary_File_1/STATENAME

# If you look for documentation, you'll see pointers to the 730-page
# PDF sf1.pdf. Don't bother: it's completely wrong and must be for
# some earlier dataset.

# Instead, the documentation is in the files inside:
# http://www.census.gov/support/2000/SF1/SF1SAS.zip
# inside which, SF101.Sas describes the fields in st00001.uf1
# where st is the state abbreviation.

import os, sys
import re
import zipfile
from collections import OrderedDict

def codesFromZipFile(zipfilename):
    zf = zipfile.ZipFile(zipfilename, 'r')
    pat = re.compile(b" *(P[0-9]{6})=' *(.*)'")
    codes = []
    for name in zf.namelist():
        if not name.lower().endswith('.sas'):
            continue
        code_dict = OrderedDict()
        # basename = os.path.basename(name)
        # root, ext = os.path.splitext(basename)
        saslines = zf.read(name).split(b'\n')
        for line in saslines:
            m = re.match(pat, line)
            if m:
                code, desc = [ s.decode() for s in m.groups() ]
                # print("%7s -- %s" % (code, desc))
                code_dict[code] = desc
            # else:
            #     print("No match on line:", line)

        codes.append(code_dict)

    return codes


if __name__ == '__main__':
    # Pass in the path to SF1SAS.zip
    codes = codesFromZipFile(sys.argv[1])
    from pprint import pprint
    pprint(codes)

