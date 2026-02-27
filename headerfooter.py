#!/usr/bin/env python3

# Copyright 2021 by Akkana; share and enjoy under the GPLv2 or later.

long_description = """
Usage: headerfooter.py file.html [file.html ...]

Take standalone HTML files and add customized headers and footers
to make them fit in with a website, replacing anything up to and
including <body> and following and including </body>.
(So your template should include <body> and </body>.
This is so your template can include the title as both
<title> and <h1>.)

This is useful if someone keeps sending you Word documents;
word2html can convert them, but this can help fit them into a
website. Can apply different headers/footers depending on the file's
location in the filesystem.

Configuration: create a directory ~/.config/headerfooter. In it,
create files with names corresponding to directory names where you
want files matched.

For example, if you keep files in a directory called myweb,
create a file named ~/.config/headerfooter/myweb.
Inside it, put your desired header and footer, separated
by two empty lines. (If you actually want two empty lines
in your HTML file, sorry, you're out of luck.)
If there aren't two empty lines in the file, the whole file
will be presumed to be a header, and no footer will be added.

headerfooter will try to figure out a page title from the content.
In your template, use $TITLE for any place you'd like this title
to be inserted.
"""


import re
import sys, os

configdir = os.path.expanduser("~/.config/headerfooter")
patfiles = os.listdir(configdir)

def do_file(filename, patname=None):
    fullpath = os.path.abspath(filename)
    if not patname:
        for pf in patfiles:
            if pf in fullpath:
                patname = pf
                break

    if not patname:
        raise(RuntimeError(filename + " doesn't match any known pattern file"))

    head, foot = read_patfile(os.path.join(configdir, patname))

    seen_body = False
    title = find_title(filename)
    print("Using title", title)
    if title:
        head = head.replace("$TITLE", title)

    outstr = head

    def write_file():
        os.rename(filename, os.path.join(filename + ".bak"))
        with open(filename, "w") as ofp:
            ofp.write(outstr)
        print("Added headers and footers to", filename)


    # Save anything before the <body> tag:
    # if it turns out there is no <body> tag, this will be the whole file.
    before_body = ""

    with open(filename) as fp:
        for line in fp:
            stripline = line.strip().lower()    # for string comparisons
            if not seen_body:
                if stripline == "<body>":
                    seen_body = True
                else:
                    before_body += "\n" + line
                continue

            # Saw the body already. Keep appending lines until </body>
            if stripline != "</body>":
                outstr += line
                continue

            outstr += foot

            write_file()

    if seen_body:
        return

    # No body. outstr contains only the desired headers.
    outstr += before_body
    outstr += foot
    write_file()


def find_title(filename):
    with open(filename) as fp:
        for line in fp:
            match = re.match("<h1>(.*)</h1>", line, flags=re.IGNORECASE)
            if match:
                return match.group(1)
            match = re.match("<title>(.*)</title>", line, flags=re.IGNORECASE)
            if match:
                return match.group(1)
            match = re.match("<strong>(.*)</strong>", line, flags=re.IGNORECASE)
            if match:
                return match.group(1)
            match = re.match("<bold>(.*)</bold>", line, flags=re.IGNORECASE)
            if match:
                return match.group(1)

    # Nothing? Use the filename
    return os.path.basename(filename).replace("_", " ")


def read_patfile(patfilename):
    with open(patfilename) as fp:
        filecontents = fp.read()

    if filecontents.startswith("\n\n"):
        head = ""
        foot = filecontents[2:]
    elif "\n\n\n" in filecontents:
        head, foot = filecontents.split("\n\n\n")
        # The first of the three newlines was the end of the previous line.
        # Add it back.
        head += "\n"
    else:
        head = filecontents
        foot = ""

    return head, foot


if __name__ == '__main__':
    if len(sys.argv) == 1 or sys.argv[1] == "-h" or sys.argv[1] == "--help":
        print(long_description)
        sys.exit(0)
    elif sys.argv[1] == "-p":
        php_extension = True

    saw_err = False
    for f in sys.argv[1:]:
        try:
            do_file(f)
        except RuntimeError as e:
            print(str(e))
            saw_err = True

    if saw_err:
        print("Known patterns:", ' '.join(patfiles))



