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
    pat = re.compile(b" *([A-Z][0-9]{3}[0-9A-Z]{3,4})=' *(.*)'")
    codes = []
    for name in zf.namelist():
        if not name.lower().endswith('.sas'):
            continue
        if not re.match('sf[0-9]{3}.sas', name.lower()):
            continue
        code_dict = OrderedDict()
        # basename = os.path.basename(name)
        # root, ext = os.path.splitext(basename)

        # Every file stars with these five, which don't have p-numbers
        code_dict['FILEID'] = 'File Identification'
        code_dict['STUSAB'] = 'State/U.S.-Abbreviation (USPS)'
        code_dict['CHARITER'] = 'Characteristic Iteration'
        code_dict['CIFSN'] = 'Characteristic Iteration File Sequence Number'
        code_dict['LOGRECNO'] = 'Logical Record Number'

        saslines = zf.read(name).split(b'\n')
        for line in saslines:
            m = re.match(pat, line)
            if m:
                pcode, desc = [ s.decode() for s in m.groups() ]
                # print("%7s -- %s" % (code, desc))
                code_dict[pcode] = desc
            # else:
            #     print("No match on line:", line)

        codes.append(code_dict)

    return codes


if __name__ == '__main__':
    # Pass in the path to SF1SAS.zip
    allcodes = codesFromZipFile(sys.argv[1])
    for i, codes in enumerate(allcodes):
        print("\n==== File", i+1)
        for pcode in codes:
            print("%7s: %s" % (pcode, codes[pcode]))

