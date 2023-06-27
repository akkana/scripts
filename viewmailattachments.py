#! /usr/bin/env python

# Take an mbox HTML message (e.g. from mutt), split it
# and rewrite it so it can be viewed in an external browser.
# Can be run from within a mailer like mutt, or independently
# on a single message file.
#
# Usage: viewhtmlmail.py email_message_file
#
# Inspired by John Eikenberry <jae@zhar.net>'s view_html_mail.sh
# which sadly no longer works, at least with mail from current Apple Mail.
#
# Copyright 2013-2022 by Akkana Peck. Share and enjoy under the GPL v2 or later.
# Contributions:
#   Holger Klawitter 2014: create a secure temp file and avoid temp mbox
#   Antonio Terceiro 2018: Allow piping directly from mutt.

# To use it from mutt, install it somewhere in your path,
# then put the following lines in your .muttrc:
# macro index <F9> "<pipe-message>~/bin/viewhtmlmail.py\n" "View HTML email in browser"
# macro pager <F9> "<pipe-message>~/bin/viewhtmlmail,ot\n" "View HTML email in browser"

# TESTING: Use the email file in test/files/htmlmail.eml.

import os, sys
import re
import time
import shutil
import email, mimetypes
from email.parser import BytesParser
from email.policy import default as default_policy
import subprocess
from collections import OrderedDict   # for python < 3.7


################################################
# Some prefs:

# Print lots of debugging info?
DEBUG = False

# If IMAGE_VIEWER is set, a message that has no multipart/related
# images will use the image viewer rather than a browser window
# for images. To use a browser, set IMAGE_VIEWER = None.
IMAGE_VIEWER = "pho"
# IMAGE_VIEWER = None
IMAGE_VIEWER_ARGS = ["-P"]   # For pho, don't use presentation mode

USE_WVHTML_FOR_DOC = False

# How many seconds do we need to wait for unoconv?
# It defaults to 6, but on a 64-bit machine that's not nearly enough.
# Even 10 often isn't enough.
UNOCONV_STARTUP_TIME = "14"

# A list of supported browsers, in order of preference.
BROWSERS = OrderedDict([
    ('qutebrowser', {
        'ARGS_FIRST': [ "--target", "private-window",
                        "--basedir", "/tmp/mailattachments",
                        "-s", "content.dns_prefetch", "false",
                        "-s", "content.javascript.enabled", "false" ],
        # If using PDFJS, add: "-s", "content.javascript.enabled", "false" 
        'ARGS': [ "--target", "tab-bg",
                  "--basedir", "/tmp/mailattachments",
                  # Don't need to specify privacy, prefetch or JS
                  # because it's being opened in a window that
                  # already has those settings, using the same configdir.
                 ],
        'BACKGROUND': True,
        # qutebrowser can display PDF natively if you use pdf.js.
        # On debian, apt install libjs-pdf.
        # But that also gives hundreds of lines of errors like
        # ERROR: NotFoundError while handling qute://* URL: Can't find pdfjs resource 'web/images/toolbarButton-viewAttachments.svg'
        # Also, it creates two tabs for each PDF file, reproducible with:
        #   qutebrowser --target private-window --basedir /tmp/mailattachments -s content.dns_prefetch false -s content.pdfjs true somefile.html
        #   qutebrowser --target tab-bg --basedir /tmp/mailattachments -s content.pdfjs true somefile.pdf
        # so for now, disable it and convert to html instead:
        'CONVERT_PDF_TO_HTML': True
    } ),

    ('quickbrowse', {
        'ARGS_FIRST': [],
        'ARGS':[ "--new-tab"],
        'BACKGROUND': False,
        'CONVERT_PDF_TO_HTML': True
    }),

    ('firefox', {
        'ARGS_FIRST': [ "--new-tab", "--private-window" ],
        'ARGS': [  "--private-window" ],
        'BACKGROUND': True,
        'CONVERT_PDF_TO_HTML': False,
    })
])

WORKING_BROWSER = None

# First call to a browser?
first_browser = True


def run_browser(browser, htmlfile):
    """Call a specific browser with the appropriate arguments.
       May raise various errors.
    """
    cmd = [ browser ]

    if first_browser:
        cmd += BROWSERS[browser]['ARGS_FIRST']
    else:
        cmd += BROWSERS[browser]['ARGS']

    cmd.append("file://" + htmlfile)
    if DEBUG:
        print("Calling in background: %s" % ' '.join(cmd))
    mysubprocess.call_bg(cmd)


def call_some_browser(htmlfile):
    """Try the list of browsers to find which one works."""
    global WORKING_BROWSER
    global first_browser
    errstr = ""

    if DEBUG:
        print("Calling browser for file://%s" % htmlfile)

    if WORKING_BROWSER:
        run_browser(WORKING_BROWSER, htmlfile)
        return

    for b in BROWSERS:
        try:
            run_browser(b, htmlfile)
            # If it worked, break out of the loop
            WORKING_BROWSER = b
            first_browser = False
            break
        except Exception as e:
            thiserr = "\n**** Couldn't run %s! %s" % (b, e)
            errstr += thiserr
            if DEBUG:
                print(thiserr)
                # traceback.print_exc()
            continue

    if not WORKING_BROWSER:
        print("Couldn't use any known browser: bailing.")
        print("Errors:", errstr)
        print("Run with -d (debug) to see more details.")
        sys.exit(1)


# Seconds to wait between refreshes when waiting for translated content
REDIRECT_TIMEOUT = 2

# End global prefs
################################################


def find_first_maildir_file(maildir):
    """Maildir: inside /tmp/mutttmpbox, mutt creates another level of
       directory, so the file will be something like /tmp/mutttmpbox/cur/1.
       So recurse into directories until we find an actual mail file.
       Return a full path to the filename.
    """
    for root, dirs, files in os.walk(maildir):
        for f in files:
            if not f.startswith('.'):
                return os.path.join(root, f)
    return None


MAX_FILENAME_LENGTH = 225

def sanitize_filename(badstr):
    """Sanitize a filename to make sure there's nothing dangerous, like ../
       Also make sure it's under MAX_FILENAME_LENGTH.
    """
    filename = ''.join([x for x in badstr if x.isalpha() or x.isdigit()
                      or x in '-_.'])
    if len(filename) > MAX_FILENAME_LENGTH:
        half = MAX_FILENAME_LENGTH // 2
        filename = filename[:half] + filename[-half:]

    return filename


def view_html_message(f, tmpdir):
    # Note: the obvious way to read a message is
    #   with open(f) as fp: msg = email.message_from_file(fp)
    # What the docs don't tell you is that that gives you an
    # email.message.Message, which is limited and poorly documented;
    # all the documentation assumes you have an email.message.EmailMessage,
    # but to get that you need the more complicated BytesParser method below.
    # The policy argument to BytesParser is mandatory: without it,
    # again, you'll get a Message and not an EmailMessage.
    if f:
        if os.path.isdir(f):
            # Maildir: f is a maildir like /tmp/mutttmpbox,
            # and inside it, for some reason, mutt creates another
            # level of directory named either cur or new
            # depending on whether the message is already marked read.
            # So we have to open the first file inside either cur or new.
            # In case mutt changes this behavior, let's take the first
            # non-dotfile inside the first non-dot directory.
            msg = None
            for maildir in os.listdir(f):
                with open(find_first_maildir_file(f), 'rb') as fp:
                    msg = BytesParser(policy=default_policy).parse(fp)
                    break
        else:
            # Mbox format: we assume there's only one message in the mbox.
            with open(f, 'rb') as fp:
                # msg = email.message_from_string(fp.read())
                msg = BytesParser(policy=default_policy).parse(fp)
    else:
        msg = BytesParser(policy=default_policy).parsebytes(sys.stdin.buffer.read())

    counter = 1
    filename = None
    filenames = set()
    subfiles = {}    # A dictionary mapping content-id to [filename, part]
    html_parts = []

    # For debugging:
    def print_part(part):
        print("*** part:")   # parts are type email.message.Message
        print("  content-type:", part.get_content_type())
        print("  content-disposition:", part.get_content_disposition())
        print("  content-id:", part.get('Content-ID'))
        print("  filename:", part.get_filename())
        print("  is_multipart?", part.is_multipart())

    def print_structure(msg, indent=0):
        """Iterate over an EmailMessage, printing its structure"""
        indentstr = ' ' * indent
        for part in msg.iter_parts():
            print("%scontent-type:" % indentstr, part.get_content_type())
            print("  content-subtype:", part.get_content_subtype())
            print("  content-id:", part.get('Content-ID'))
            print("%scontent-disposition:" % indentstr,
                  part.get_content_disposition())
            print("%sfilename:" % indentstr, part.get_filename())
            print("%sis_multipart?" % indentstr, part.is_multipart())
            print_structure(part, indent=indent+2)
            print()

    if DEBUG:
        print_structure(msg)

    for part in msg.walk():
        if DEBUG:
            print()
            print_part(part)

        # multipart/* are just containers
        #if part.get_content_maintype() == 'multipart':
        if part.is_multipart() or part.get_content_type == 'message/rfc822':
            continue

        # Get the content id.
        # Mailers may use Content-Id or Content-ID (or, presumably, various
        # other capitalizations). So we can't just look it up simply.
        content_id = None
        for k in list(part.keys()):
            if k.lower() == 'content-id':
                # Remove angle brackets, if present.
                # part['Content-Id'] is unmutable -- attempts to change it
                # are just ignored -- so copy it to a local mutable string.
                content_id = part[k]
                if content_id.startswith('<') and content_id.endswith('>'):
                    content_id = content_id[1:-1]

                counter += 1

                break     # no need to look at other keys

        if part.get_content_subtype() == 'html':
            if DEBUG:
                print("Found an html part")
                if html_parts:
                    print("Eek, more than one html part!")
            html_parts.append(part)

        elif not content_id:
            if DEBUG:
                print("No Content-Id")
            pass

        # Use the filename provided if possible, otherwise make one up.
        filename = part.get_filename()

        if filename:
            filename = sanitize_filename(filename)
        else:
            # if DEBUG:
            #     print("No filename; making one up")
            ext = mimetypes.guess_extension(part.get_content_type())
            if not ext:
                # Use a generic bag-of-bits extension
                ext = '.bin'
            if content_id:
                filename = sanitize_filename('cid%s%s' % (content_id, ext))
            else:
                filename = 'part-%03d%s' % (counter, ext)

        # Some mailers, like gmail, will attach multiple images to
        # the same email all with the same filename, like "image.png".
        # So check whether we have to uniquify the names.
        if filename in filenames:
            orig_basename, orig_ext = os.path.splitext(filename)
            dedup_counter = 0
            while filename in filenames:
                dedup_counter += 1
                filename = "%s-%d%s" % (orig_basename, dedup_counter, orig_ext)

        filenames.add(filename)

        # If there's no content_id, use the uniquified filename, sans path.
        if not content_id:
            content_id = filename

        filename = os.path.join(tmpdir, filename)

        # Now save content to the filename, and remember it in subfiles.
        subfiles[content_id] = [ filename, part ]
        with open(filename, 'wb') as fp:
            fp.write(part.get_payload(decode=True))
            if DEBUG:
                print("wrote", filename)

        # print "%10s %5s %s" % (part.get_content_type(), ext, filename)

    if DEBUG:
        print("\nsubfiles now:", subfiles)
        print()

    # We're done saving the parts. It's time to save the HTML part(s),
    # with img tags rewritten to refer to the files we just saved.
    embedded_parts = []
    for i, html_part in enumerate(html_parts):
        htmlfile = os.path.join(tmpdir, "viewhtml%02d.html" % i)
        fp = open(htmlfile, 'wb')

        # html_parts[i].get_payload() returns string, but it's apparently
        # in straight unicode and doesn't reflect the message's charset.
        # html_part.get_payload(decode=True) returns bytes,
        # which (I think) have been decoded as far as email transfer
        # (e.g. Content-Encoding: base64), which is not the same thing
        # as charset decoding.
        # (None of this is documented in the python3 email module;
        # there's no mention of get_payload() at all. Sigh.)

        htmlsrc = html_part.get_payload(decode=True)

        # Substitute all the filenames for content_ids:
        for sf_cid in subfiles:
            # Yes, yes, I know:
            # https://stackoverflow.com/questions/1732348/regex-match-open-tags-except-xhtml-self-contained-tags/
            # and this should be changed to use BeautifulSoup.
            if DEBUG:
                print("Replacing cid", sf_cid, "with", subfiles[sf_cid][0])
            newhtmlsrc = re.sub(b'cid: ?' + sf_cid.encode(),
                                b'file://' + subfiles[sf_cid][0].encode(),
                                htmlsrc, flags=re.IGNORECASE)
            if sf_cid not in embedded_parts and newhtmlsrc != htmlsrc:
                embedded_parts.append(sf_cid)
            htmlsrc = newhtmlsrc

        fp.write(htmlsrc)
        fp.close()
        if DEBUG:
            print("Wrote", htmlfile)

        # Now we have the file. Call a browser on it.
        call_some_browser(htmlfile)

    # Done with htmlparts.
    # Now handle any parts that aren't embedded inside HTML parts.
    # This includes conversions from Word or PDF, but also image attachments.
    if DEBUG:
        print()
        print("subfiles:", subfiles)
        print("Parts already embedded:", embedded_parts)
        print("\n************************************\n")

    image_files = []
    for sfid in subfiles:
        if DEBUG:
            print("\nPart:", subfiles[sfid][0])
        part = subfiles[sfid][1]
        partfile = subfiles[sfid][0]    # full path
        fileparts = os.path.splitext(partfile)

        if sfid in embedded_parts:
            if DEBUG:
                print(partfile, "was already embedded in html")
            continue

        if part.get_content_maintype() == "image":
            image_files.append(partfile)
            continue

        if part.get_content_maintype() == "application":
            htmlfilename = fileparts[0] + ".html"

            subtype = part.get_content_subtype()
            if DEBUG:
                print("Application subtype:", subtype)
            is_word = ("msword" in subtype or "ms-word" in subtype)
            if is_word and USE_WVHTML_FOR_DOC:
                mysubprocess.call(["wvHtml", partfile, htmlfilename])
                call_some_browser(htmlfilename)
                continue

            # Unfortunately, unoconv can't convert excel files:
            # it hangs forever trying.
            if (is_word or subtype ==
                "vnd.openxmlformats-officedocument.wordprocessingml.document"
                or subtype == "vnd.oasis.opendocument.text"):
                mysubprocess.call(["unoconv", "-f", "html",
                                      "-T", UNOCONV_STARTUP_TIME,
                                      "-o", htmlfilename, partfile])
                call_some_browser(htmlfilename)
                continue

            # unoconv conversions from powerpoint to HTML drop all images.
            # Try converting to PDF instead:
            if part.get_content_subtype() == "vnd.ms-powerpoint" \
                 or part.get_content_subtype() == \
              "vnd.openxmlformats-officedocument.presentationml.presentation":
                pdffile = fileparts[0] + ".pdf"
                mysubprocess.call(["unoconv", "-f", "pdf",
                                      "-o", pdffile, partfile])
                partfile = pdffile

            if part.get_content_subtype() == "pdf" or partfile.endswith("pdf"):
                if WORKING_BROWSER and \
                   BROWSERS[WORKING_BROWSER]['CONVERT_PDF_TO_HTML']:
                    print("Calling pdftohtml and delaying browser")
                    mysubprocess.call(["pdftohtml", "-s", partfile])
                    print("pdftohtml exited. Did it work?")
                    fff = fileparts[0] + "-html.html"
                    os.system("ls -l " + fff)

                    # But pdftohtml is idiotic about output filename
                    # and won't let you override it:
                    call_some_browser(fileparts[0] + "-html.html")
                else:
                    call_some_browser(partfile)

    if image_files:
        if IMAGE_VIEWER:
            if DEBUG:
                print("Calling", IMAGE_VIEWER, "on", image_files)
            cmd = [ IMAGE_VIEWER ] + IMAGE_VIEWER_ARGS + image_files
            mysubprocess.call_bg(cmd)
        else:
            for img in image_files:
                call_some_browser(img)


# For debugging:
class mysubprocess:
    @staticmethod
    def call(arr):
        if DEBUG:
            print("\n========= Calling: %s" % str(arr))
        subprocess.call(arr)

    @staticmethod
    def call_bg(arr):
        if DEBUG:
            print("\n========= Calling in background: %s"
                  % str(arr))
        subprocess.Popen(arr, shell=False,
                         stdin=None, stdout=None, stderr=None)


if __name__ == '__main__':
    import tempfile

    tmpdir = tempfile.mkdtemp()
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            if f == '-d':
                DEBUG = True
                continue
            view_html_message(f, tmpdir)
    else:
        view_html_message(None, tmpdir)
