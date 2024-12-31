#!/usr/bin/env python3

# Make a diff of the *text* in two Word files, ignoring line breaks
# and formatting.

# For .docx, use pandoc to convert both documents to markdown.
# For .doc, use wvText to convert both documents to text.

import subprocess
import os.path
import sys


def diff_docx(file1, file2, remove_tmp_files=True):
    # Convert both files to markdown
    mdfile1 = os.path.splitext(file1)[0] + '.md'
    docx_to_md(file1, mdfile1)
    mdfile2 = os.path.splitext(file2)[0] + '.md'
    docx_to_md(file2, mdfile2)

    print("Differences between", mdfile1, "and", mdfile2, ":")
    subprocess.call(['diff', mdfile1, mdfile2])

    if remove_tmp_files:
        os.unlink(mdfile1)
        os.unlink(mdfile2)


def diff_doc(file1, file2, remove_tmp_files=True):
    # Convert both files to text
    tfile1 = os.path.splitext(file1)[0] + '.txt'
    doc_to_txt(file1, tfile1)
    tfile2 = os.path.splitext(file2)[0] + '.txt'
    doc_to_txt(file2, tfile2)

    print("Differences between", tfile1, "and", tfile2, ":")
    subprocess.call(['diff', tfile1, tfile2])

    if remove_tmp_files:
        os.unlink(tfile1)
        os.unlink(tfile2)


def doc_to_txt(infile, outfile):
    subprocess.call(["wvText", infile, outfile])


def docx_to_md(infile, outfile):
    subprocess.call(["pandoc", "-f", "docx", "-t", "markdown", infile,
                     "-o", outfile])


def diff_word_files(file1, file2, remove_tmp_files=True):
    ext = os.path.splitext(file1)[1]
    if os.path.splitext(file2)[1] != ext:
        print("File changed extension")
        return
    if ext == '.doc':
        diff_doc(file1, file2)
    else:
        diff_docx(file1, file2)


if __name__ == '__main__':
    diff_word_files(sys.argv[1], sys.argv[2], True)

