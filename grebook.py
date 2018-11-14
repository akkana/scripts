#!/usr/bin/env python3

import sys, os
import subprocess

'''
    unzip -p $i "*.htm*" "*.xml" "*.opf" |  # unzip only html and content files to stdin
    perl -lpe 's![<][^>]{1,200}?[>]!!g;' | # get rid of small html <b>tags
    grep -Piaso  ".{0,30}$PAT.{0,30}" |    # keep some context around matches
    grep -Pi --color "$PAT"                # color the matches.
'''

def grep_ebook(pat, filename):
    print(['unzip', '-p', filename, '*.htm*', '*.xml', '*.opf'])
    p1 = subprocess.Popen(['unzip', '-p', filename,
                           '*.htm*', '*.xml', '*.opf'],
                          shell=False, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['perl', '-lpe', 's![<][^>]{1,200}?[>]!!g;'],
                          shell=False, stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    p3 = subprocess.Popen(['grep', '-Piaso', '.{0,30}%s.{0,30}' % pat],
                          shell=False, stdin=p2.stdout,stdout=subprocess.PIPE)
    p2.stdout.close()
    p4 = subprocess.Popen(['grep', '-Pi', '--color', pat],
                          shell=False, stdin=p3.stdout,stdout=subprocess.PIPE)
    p3.stdout.close()

    output = p4.communicate()[0]
    print(output)


if __name__ == '__main__':
    grep_ebook(sys.argv[1], sys.argv[2])

