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
# into a directory called html, then convert the agenda file to
# html using mammoth, with links to the right converted files.
# It will also make a zip file of everything.

from bs4 import BeautifulSoup
import os, sys

from word2html import docx2html

from difflib import SequenceMatcher

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
    else:
        print("Agenda must be .html or .docx")
        sys.exit(1)

    origdir, agendafilename = os.path.split(agenda_infile)
    basedir, origdirname = os.path.split(origdir)
    if origdirname == "orig":
        htmldir = os.path.join(basedir, "html")
    elif origdirname == 'html':
        htmldir = origdirname
        origdirname = os.path.join(basedir, "orig")
        origdir = os.path.join(basedir, origdirname)
    else:
        print("Infile name should be a in a directory named 'orig'")
        sys.exit(1)

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
    converted = []
    already_converted = []

    for em in soup.findAll('em'):
        # em_text = os.path.splitext(em.text.strip())[0]
        em_text = em.text.strip()

        # Remove empty <em>s
        if not em_text:
            em.extract()
            continue

        # Strip off any extension, if any.
        # But this doesn't work because there might be dots in the filename,
        # e.g. 10.1_CNM_Report_03.2021
        # em_text, fileext = os.path.splitext(em_text)

        # First see if there's an html file by that name
        if em_text in htmlbases:
            a = soup.new_tag("a", href="html/" + em_text + ".html",
                             target="_blank")
            a.string = em_text
            em.contents[0].replace_with(a)
            em_text = None
            continue

        # Not already HTML. Find the original file and convert, if possible.
        # Can't just search for em_text in origbases, because
        # non-technical users seem incapable of understanding
        # "put the filename in the agenda", and will instead put
        # something that vaguely resembles the filename, e.g.
        # the agenda might have "Budget proposal FY 21-23" where
        # the actual filename is "45. Budget proposal FY 21-23.pdf".
        # elif em_text in origbases:
        def fuzzy_search(agendaname, filenames):
            # First try non-fuzzy, with fingers tightly crossed
            if agendaname in filenames:
                return filenames.index(agendaname)
            # No luck there, try fuzzy matches
            best_ratio = -1
            best_match = None
            for i, filename in enumerate(filenames):
                if agendaname in filename:
                    return i
                r = SequenceMatcher(None, agendaname, filename).ratio()
                if r > best_ratio:
                    best_match = i
                    best_ratio = r
            if best_ratio > .75:
                print("Guessing", agendaname, "-->", filenames[best_match])
                return best_match
            return -1

        index = fuzzy_search(em_text, origbases)
        if index < 0:    # No fuzzy match
            print("Couldn't find a match for", em_text)
            continue

        # Found a match by searching origbases, returning index.
        # So the actal original file is origfiles[index].

        origfile = origfiles[index]
        origbase, ext = os.path.splitext(origfile)
        if ext == ".docx" or ext == ".doc":
            # Use unoconv because it preserves colors,
            # which mammoth/word2html does not.
            infile = os.path.join(origdir, origfile)
            # Replace any spaces in the HTML filename with underscores
            # in case that hasn't already been done.
            htmlfile = origbase.replace(' ', '_') + ".html"
            outfile = os.path.join(htmldir, htmlfile)

            # Maybe it's already been converted in an earlier run
            if not os.path.exists(outfile):
                # For some reaason, unoconv flakes out when you try to
                # call it from inside a python script, even if it
                # works just fine from the shell. The error message is:
                #    unoconv: Cannot find a suitable pyuno library
                #             and python binary combination in
                #             /usr/lib/libreoffice
                # The cure: specify the full path to both python and unoconv.
                # No one seems to understand why.
                rv = subprocess.call(["/usr/bin/python3", "/usr/bin/unoconv",
                                      "-f", "html", "-T", "10",
                                      "-o", outfile, infile])
                if not rv:
                    converted.append(origfile)
                else:
                    cantconvert.append(origfile)
                    # print("unoconv failed on", filename, "exit code", rv)
            else:
                already_converted.append(origfile)
                # print(outfile, "was already converted")

            if os.path.exists(outfile):
                htmlfile = "html/" + htmlfile
                a = soup.new_tag("a", href=htmlfile, target="_blank")
                a.string = em_text
                em.contents[0].replace_with(a)
                htmlfiles.append(htmlfile)
                em_text = None
        else:
            cantconvert.append(origfile)
            linkfile = "orig/" + origfile
            a = soup.new_tag("a", href=linkfile, target="_blank")
            a.string = em_text
            em.contents[0].replace_with(a)
            em_text = None

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
    # print("allfiles:")
    # for f in allfiles:
    #     print("  ", f)

    rv = subprocess.call(["zip", os.path.join(zipname, zipfile), *allfiles])
    if not rv:
        print("zip file is:", zipfile)
    else:
        print("Couldn't save zip file")

    # Add a link to the zip file in the agenda:
    tag = soup.new_tag("hr")
    soup.body.append(tag)
    tag = soup.new_tag("a", href=zipfile, target="_blank")
    tag.string = "Zip file of everything"
    soup.body.append(tag)

    # Finally, the agenda is ready to write.
    agenda_out = os.path.join(basedir, "index.html")
    with open(agenda_out, "w") as outfp:
        outfp.write(soup.prettify())
    print("Wrote agenda", agenda_out)

    # Finally, print stats.
    if already_converted:
        print("\nAlready converted:")
        for f in already_converted:
            print("    ", f)

    if converted:
        print("\nConverted:")
        for f in converted:
            print("    ", f)

    if cantconvert:
        print("\nCan't convert:")
        for f in cantconvert:
            print("    ", f)

    if nosuchfiles:
        print("\nCouldn't find files:")
        for f in nosuchfiles:
            print("    ", f)


if __name__ == '__main__':
    fix_agenda(sys.argv[1])

