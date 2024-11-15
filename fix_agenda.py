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

from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
import os, sys

from word2html import docx2html, docx2htmlfile

from difflib import SequenceMatcher

import subprocess
# uno_env = os.environ.copy()
# uno_env['HOME'] = '/tmp'
# uno_env["UNOPATH"] ="/usr/bin/libreoffice"

VERBOSE = True

# A list of extensions we might expect to find in original files.
# This is because the agenda might omit extensions, and we also can't
# assume that a dot indicates an extension.
# For example, the agenda might have '9.3_LA_Report_11.2024'
# which is expected to match '9.3_LA_Report_11.2024.docx', and you
# can't just strip off everything after the last dot because then
# you lose the '2024'. Sigh!
ORIG_EXTENSIONS = [ '.doc', '.docx', '.odt',
                    '.xls', '.xlsx', '.csv'
                  ]

# Remove extension: can't just use os.path.splitext
# because there might be dots in the filename,
# e.g. 10.1_CNM_Report_03.2021
def smart_splitext(aname):
    """Strip off any extension matching something in ORIG_EXTENSIONS.
    """
    name, ext = os.path.splitext(aname)
    if ext.lower() in ORIG_EXTENSIONS:
        return name, ext
    return aname, ''


def legalchars(fname):
    """Remove illegal characters from filenames"""
    return''.join([x for x in fname if x.isalpha() or x.isdigit() \
                   or x in '-_.'])


def fix_agenda(agenda_infile):
    # Convert agenda_infile to absolute path
    agenda_infile = os.path.abspath(agenda_infile)

    # First convert the agenda, if needed
    agenda_base, agenda_ext = smart_splitext(agenda_infile)
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
        print("Infile name should be a in a directory named 'orig' or 'html'")
        sys.exit(1)

    # The title comes out as /full/path/to/filename.html
    # How to change a title is completely undocumented,
    # but it turns out to be title.string.
    title = soup.title.string
    if '/' in title:
        title = os.path.basename(title)
        soup.title.string = title

    # Convert any existing links to be target="_blank"
    for link in soup.find_all("a"):
        if link.attrs["href"] and not link.attrs["href"].startswith("#"):
            link.attrs["target"] = "_blank"

    origfiles = os.listdir(origdir)
    origbases = [ smart_splitext(f)[0] for f in origfiles ]
    if not os.path.exists(htmldir):
        os.mkdir(htmldir)
    htmlfiles = os.listdir(htmldir)
    htmlbases = [ smart_splitext(f)[0] for f in htmlfiles ]

    # Read the list of original filenames, in subdir orig.
    # with bad filename characters removed.
    origfiles = []
    for fname in os.listdir("orig"):
        newfname = legalchars(fname)
        if newfname != fname:
            print("** Renaming '%s' to '%s'" % (fname, newfname))
            os.rename(os.path.join('orig', fname),
                      os.path.join('orig', newfname))
        origfiles.append(newfname)

    # List of already existing html filenames, in subdir html.
    # We'll add to this list as files are converted to html.
    htmlfiles = os.listdir("html")

    nosuchfiles = []
    cantconvert = []
    converted = []
    already_converted = []
    guesses = {}

    for em in soup.findAll('em'):
        # em_text = smart_splitext(em.text.strip())[0]
        em_text = em.text.strip()

        # Remove empty <em>s
        if not em_text:
            em.extract()
            continue

        em_text = legalchars(em_text)

        if VERBOSE:
            print("\n===", em_text)

        # Find the original file.
        # Can't just search for em_text in origbases,
        # because non-technical users don't seem to grok
        # "put the filename in the agenda", and will instead put
        # something that vaguely resembles the filename, e.g.
        # the agenda might have "Budget proposal FY 21-23" where
        # the actual filename is "45. Budget proposal FY 21-23.pdf".
        # elif em_text in origbases:
        def fuzzy_search(agendaname, filenames):
            """If agendaname is a filename referenced in the agenda,
               try to match it in the list filenames,
               returning the index into the list, or -1 if no match.
               If there's no exact match, use fuzzy search and also
               be tolerant of missing extensions.
            """
            agendaname, fileext = smart_splitext(agendaname)
            filenames_no_ext = [ os.path.splitext(f)[0] for f in filenames ]

            if agendaname in guesses:
                return filenames.index(guesses[agendaname])

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

            if best_ratio > .88:
                return best_match

            return -1

        def replace_em(href):
            nonlocal em, em_text
            a = soup.new_tag("a", href=href, target="_blank")
            a.string = em_text
            em.contents[0].replace_with(a)
            em_text = None

        def append_parenthesized_orig(em, origfile):
            # Add a parenthesizedlink to the original document.
            # This doesn't end up getting called for every .doc* file, though.
            base, ext = smart_splitext(origfile)
            em.append(NavigableString(" (original "))
            linkfile = "orig/" + origfile
            a = soup.new_tag("a", href=linkfile, target="_blank")
            a.string = ext
            em.append(a)
            em.append(NavigableString(")"))

        index = fuzzy_search(em_text, origbases)
        htmlindex = fuzzy_search(em_text, htmlbases)

        if index < 0 and htmlindex < 0:    # No exact or fuzzy match
            print("Couldn't find a match for", em_text)
            nosuchfiles.append(em_text)
            continue

        if index > 0 and origbases[index] != em_text:
            guesses[em_text] = origbases[index]

        # Is the html match fuzzy but the original match not?
        # e.g. if origfiles include 9.1_CNM_Report_03.2024.docx and
        # 9.7_SNM_Report_03.2024.pdf, then there won't be an HTML file
        # for SNM but fuzzy_match for SNM will match the CNM HTML,
        # which it shouldn't.
        # print("index", index, "htmlindex", htmlindex)
        # print("origbases", origbases)
        # print("htmlbases", htmlbases)
        if index >= 0 and htmlindex >= 0 and \
           origbases[index] != htmlbases[htmlindex]:
            print("%s and %s don't match: probably not the right HTML file"
                  % (origbases[index], htmlbases[htmlindex]))
            htmlindex = -1

        # Found a match by searching origbases, returning index.
        # So the actal original file is origfiles[index].

        if index >= 0:
            origfile = origfiles[index]
            origbase, ext = os.path.splitext(origfile)

        # Is there already an HTML file matching this em?
        if htmlindex >= 0:
            orightml = htmlfiles[htmlindex]

            # an original HTML file, or one already converted from Word?
            if index >= 0:
                if VERBOSE:
                    print("  There's both Word and HTML for", origbase)
                try:
                    orig_mtime = os.stat("orig/" + origfile).st_mtime
                    html_mtime = os.stat("html/" + orightml).st_mtime
                    if orig_mtime <= html_mtime:
                        replace_em("html/" + orightml)
                        already_converted.append(origfile)
                        print("  ... The HTML was newer")
                        # Still want a link to the orig doc file, though
                        append_parenthesized_orig(em, origfile)
                        continue
                    else:
                        print("  Replacement Word file, re-converting")
                except Exception as e:
                    print("Couldn't get mtime:", e)

            # No Word file, it's just an HTML file that stands by itself
            else:
                print("standalone html file", orightml)
                replace_em("html/" + orightml)
                already_converted.append(orightml)
                continue

        # Okay, the original file isn't HTML. Is it Word?
        if ext == ".docx" or ext == ".doc":
            infile = os.path.join(origdir, origfile)
            htmlfile = origbase + ".html"
            outfile = os.path.join(htmldir, htmlfile)

            if origbase.startswith('1') and "Agenda" in origbase:
                # When converting the agenda, use mammoth because
                # there won't be colors (that we care about, anyway)
                # and it's sometimes handy to be able to edit the
                # agenda -- unoconv output is almost impossible to edit
                # without making a mistake.
                docx2htmlfile(infile, outfile)
                converted.append(origfile)
                # print("Converted the agenda %s separately" % outfile)

            else:
                # Use unoconv because it preserves colors,
                # which mammoth/word2html does not.
                #
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

            if os.path.exists(outfile):
                htmlfile = "html/" + htmlfile
                replace_em(htmlfile)
                # Don't add to htmlfiles, should be already there

            append_parenthesized_orig(em, origfile)

        else:
            if VERBOSE:
                print("Not word or html:", origfile)
            cantconvert.append(origfile)
            linkfile = "orig/" + origfile
            replace_em(linkfile)

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

    # Footer material
    tag = soup.new_tag("hr")
    soup.body.append(tag)

    # Last-modified date
    now = datetime.now()
    nowtext = NavigableString("Updated: " + now.strftime("%a %m/%d/%Y %H:%M"))
    soup.body.append(nowtext)

    tag = soup.new_tag("br")
    soup.body.append(tag)

    # link to the zip file:
    tag = soup.new_tag("a", href=zipfile)
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
        print("\nLeft untouched:")
        for f in cantconvert:
            print("    ", f)

    if guesses:
        print("\nFuzzy matches (in agenda -> actual filename):")
        for a in guesses:
            print(f"    {a} -> {guesses[a]}")
        print("BE SURE TO LOOK OVER THIS LIST!")

    if nosuchfiles:
        print("\nMissing files referenced in the agenda:")
        for f in nosuchfiles:
            print("    ", f)

    orphans = []
    for o in origfiles:
        if o not in already_converted and o not in converted \
           and o not in cantconvert:
            orphans.append(o)
    if orphans:
        orphans.sort()
        print("\nOriginal files not referenced in the agenda:")
        for o in orphans:
            print("    ", o)


if __name__ == '__main__':
    fix_agenda(sys.argv[1])

