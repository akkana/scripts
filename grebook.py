#!/usr/bin/env python3

from __future__ import print_function

import sys, os
import subprocess
import re

def grep_ebook(pat, filename):

    # unzip only html and content files to stdin
    p1 = subprocess.Popen(['unzip', '-p', filename,
                           '*.htm*', '*.xml', '*.opf'],
                          shell=False, stdout=subprocess.PIPE)

    output = p1.communicate()[0]
    p1 = re.sub('[<][^>]{1,200}?[>]', '', output)

    



    # keep some context around matches
    p3 = subprocess.Popen(['grep', '-Piaso', '.{0,30}%s.{0,30}' % pat],
                          shell=False, stdin=output, stdout=subprocess.PIPE)

    # color the matches (doesn't work for me)
    p4 = subprocess.Popen(['grep', '-Pi', '--color', pat],
                          shell=False, stdin=p3.stdout, stdout=subprocess.PIPE)
    p3.stdout.close()

    output = p4.communicate()[0]
    return output


if __name__ == '__main__':
    for book in sys.argv[2:]:
        output = grep_ebook(sys.argv[1], book)
        if output:
            print('=====', book)
            print(output)
            print()

