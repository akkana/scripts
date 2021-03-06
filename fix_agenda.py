#!/usr/bin/env python3

# The scenario:
#   Someone sends you a collection of files for an upcoming meeting,
#   in a variety of formats but predominantly .doc and .docx,
#   one of which is an agenda for the meeting.
# The goal:
#   Create a place on the website where meeting attendees can
#   view the agenda and click on links to see documents,
#   converted to HTML if possible, plus a zip file of everything
#   that they can download to their local machine.

# Make a directory for the meeting (e.g. 2021=03-06), with a
# subdirectory 2021=03-06/orig where all the original documents go.
# If there are any HTML files, put them in 2021=03-06/html.
# Then run this script passing it one argument, the agenda file,
# e.g. fix_agenda orig/1.0_Agenda_03.06.2021.docx.
# This will convert all the .doc and .docx files using unoconv
# into a directory called html, then create an agenda with links
# to the right places, along with the zip file.

from bs4 import BeautifulSoup
import os, sys

from word2html import docx2html

import subprocess
# uno_env = os.environ.copy()
# uno_env['HOME'] = '/tmp'
# uno_env["UNOPATH"] ="/usr/bin/libreoffice"


def fix_agenda(agenda_infile):
    # Convert agenda_infile to absolute path
    agenda_infile = os.path.abspath(agenda_infile)

    # First convert the agenda, if needed
    agenda_base, agenda_ext = os.path.splitext(agenda_infile)
    if agenda_ext =='.html':
        with open(agenda_infile) as fp:
            soup = BeautifulSoup(fp, "lxml")
    elif agenda_ext =='.docx':
        soup = BeautifulSoup(docx2html(agenda_infile), "lxml")

    origdir, agendafilename = os.path.split(agenda_infile)
    basedir, origdirname = os.path.split(origdir)
    if origdirname != "orig":
        print("Infile name should be a in a directory named 'orig'")
        sys.exit(1)
    htmldir = os.path.join(basedir, "html")

    origfiles = os.listdir(origdir)
    origbases = [ os.path.splitext(f)[0] for f in origfiles ]
    if not os.path.exists(htmldir):
        os.mkdir(htmldir)
    htmlfiles = os.listdir(htmldir)
    htmlbases = [ os.path.splitext(f)[0] for f in htmlfiles ]

    # Read the list of html filenames, in subdir html,
    # and original filenames, in subdir orig.
    htmlfiles = os.listdir("html")
    origfiles = os.listdir("orig")

    nosuchfiles = []
    cantconvert = []

    for em in soup.findAll('em'):
        # filebase = os.path.splitext(em.text.strip())[0]
        filebase = em.text.strip()

        # Remove empty <em>s
        if not filebase:
            em.extract()
            continue

        # Strip off any extension, if any.
        # But this doesn't work because there might be dots in the filename,
        # e.g. 10.1_CNM_Report_03.2021
        # filebase, fileext = os.path.splitext(filebase)
        # print("Now filebase is", filebase)

        # First see if there's an html file by that name
        if filebase in htmlbases:
            # print(filebase, "is already html")
            a = soup.new_tag("a", href="html/" + filebase + ".html")
            a.string = filebase
            em.contents[0].replace_with(a)
            filebase = None

        # Not already HTML. Find the original file and convert, if possible.
        elif filebase in origbases:
            filename = origfiles[origbases.index(filebase)]
            f, ext = os.path.splitext(filename)
            if ext == ".docx" or ext == ".doc":
                # Use unoconv because it preserves colors,
                # which mammoth/word2html does not.
                infile = os.path.join(origdir, filename)
                htmlfile = filebase + ".html"
                outfile = os.path.join(htmldir, htmlfile)

                # For some reaason, unoconv flakes out when you try to
                # call it from inside a python script, even if it
                # works just fine from the shell. The error message is:
                #    unoconv: Cannot find a suitable pyuno library
                #             and python binary combination in
                #             /usr/lib/libreoffice
                # The cure: specify the full path to both python and unoconv.
                rv = subprocess.call(["/usr/bin/python3", "/usr/bin/unoconv",
                                      "-f", "html", "-T", "10",
                                      "-o", outfile, infile])
                if not rv:
                    a = soup.new_tag("a", href="html/" + htmlfile)
                    a.string = filebase
                    em.contents[0].replace_with(a)
                    print("Converted", filename)
                    htmlfiles.append(filename)
                    filebase = None
                else:
                    print("unoconv failed on", filename, "exit code", rv)
            else:
                cantconvert.append(filename)
                a = soup.new_tag("a", href="orig/" + filename)
                a.string = filebase
                em.contents[0].replace_with(a)
                filebase = None

        else:
            # Couldn't find the file referenced in italics in the agenda.
            # XXX TODO: try a fuzzy search on origfiles, since the names
            # in the agenda often don't quite match the actual filenames.
            nosuchfiles.append(filebase)
            # Leave the em unchanged, no file to link to.

    if cantconvert:
        print("Can't convert:")
        for f in cantconvert:
            print("    ", f)
    if nosuchfiles:
        print("Couldn't find files:")
        for f in nosuchfiles:
            print("    ", f)

    agenda_out = os.path.join(basedir, "index.html")
    with open(agenda_out, "w") as outfp:
        outfp.write(soup.prettify())
    print("Wrote agenda", agenda_out)

    # Make sure all the originals are readable -- mutt insists on
    # saving all attachments as mode 600.
    for f in os.listdir(origdir):
        os.chmod(os.path.join(origdir, f), 0o644)

    zipname = os.path.basename(basedir)    # the base directory's name

    # Remove any zip file that was there before
    os.chdir(basedir)
    zipfile = os.path.join("%s.zip" % zipname)
    try:
        os.unlink(zipfile)
    except:
        pass

    # Now make a zip file, starting from one level above the basedir
    os.chdir("..")

    allfiles = [ os.path.join(zipname, "index.html") ] \
        + [ os.path.join(zipname, "html", f) for f in htmlfiles ] \
        + [ os.path.join(zipname, "orig", f) for f in origfiles ]
    print("allfiles:")
    for f in allfiles:
        print("  ", f)

    rv = subprocess.call(["zip", os.path.join(zipname, zipfile), *allfiles])
    if not rv:
        print("zip file is:", zipfile)
    else:
        print("Couldn't save zip file")


if __name__ == '__main__':
    fix_agenda(sys.argv[1])


