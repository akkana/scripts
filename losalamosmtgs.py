#!/usr/bin/env python3

# Scrape the Los Alamos meetings page to be alerted to what's on
# the agenda at upcoming meetings.
# Make it available via RSS.

# Suggestion: run this script via crontab:
# Use crontab -e to add a line like:
# 45  15  *  *  * python3 /path/tp/htdocs/losalamosmtgs.py > /path/to/htdocs/los-alamos-meetings/LOG 2>&1

import requests
from bs4 import BeautifulSoup, NavigableString
import datetime
from urllib.parse import urljoin
import io
import string
import subprocess
import tempfile
import json
import re
import os, sys
from lxml.html.diff import htmldiff
from urllib3.exceptions import ReadTimeoutError
from math import isclose

# Try to use PyMuPDF if available.
# For some inexplicable reason the package PyMuPDF is imported as "fitz".
try:
    import fitz
except:
    print("No PyMuPDF installed, using pdftohtml")


########## CONFIGURATION ##############
# You can also pass in RSS_URL RSS_DIR as two optional arguments

# Where to start: the public legistar meeting list
MEETING_LIST_URL = "http://losalamos.legistar.com/Calendar.aspx"

# The place where the RSS will be hosted. Must end with a slash.
# The RSS file will be this/index.rss.
RSS_URL = "http://localhost/los-alamos-meetings/"

# Where to put the generated RSS file. Customize this for your website.
RSS_DIR = os.path.expanduser("~/web/los-alamos-meetings")
if not os.path.exists(RSS_DIR):
    os.makedirs(RSS_DIR)

######## END CONFIGURATION ############

###### constants used by html_agenda_fitz ########
# Range where the left margin will normally be for headers
HEADER_COL = (50, 65)

NUMBER_HEADER_RE = re.compile('^[0-9]+\.\n[A-Z0-9]')
# Letter headers are sometimes like 6.A. and sometimes just A.
LETTER_HEADER_RE = re.compile('^[0-9\.]*[A-Z]+\.\n[A-Z0-9]')
SUBNUM_HEADER_RE = re.compile('^[0-9]+\)\n[A-Z0-9]')
######## END fitz configuration ############


# Needed to deal with meetings that don't list a time:
NO_TIME = "NO TIME"
localtz = datetime.datetime.now().astimezone().tzinfo


Verbose = True

# Make a timezone-aware datetime for now:
now = datetime.datetime.now().astimezone()

# and save the timezone
localtz = now.tzinfo

# Format for dates in RSS:
# This has to be GMT, not %Z, because datetime.strptime just
# throws away any %Z info anyway rather than parsing it.
# Better to get an error if we see any time that's not GMT.
RSS_DATE_FORMAT = "%a, %d %b %Y %H:%M GMT"

# Match the date format used in the tickler, e.g. Tue Feb 28
TICKLER_HDR_DATE_PAT = re.compile("[MTWFS][a-z]{2} [A-Z][a-z]{2} [0-9]{1,2}")

# Match the predicted agenda dates in the tickler, e.g. Agenda Date: 03/14/2023
TICKLER_AGENDA_DATE_PAT = re.compile("^Agenda Date: [0-9]+/[0-9]+/[0-9]+")

# Items are introduced with a "file number" which can help separate them
# in what otherwise looks like a sea of text.
# With fitz, the succeeding characters may include newlines,
# so it needs DOTALL.
# FILENO_PAT = re.compile('[A-Z0-9]{2,}-[A-Z0-9]{2,}')
FILENO_PAT = re.compile('([A-Z0-9]{2,}-[A-Z0-9]{2,})\s*(.*)$', flags=re.DOTALL)


# Where temp files will be created. pdftohtml can only write to a file.
tempdir = tempfile.mkdtemp()


upcoming_meetings = []


def build_upcoming_meetings_list(only_future=False):
    # By default, the calendar page only shows the current month,
    # even when there are meetings scheduled for next month.
    # To see anything from the upcoming month you have to set cookies
    # in the HTTP request.
    # If you do that manually, here are the cookies it sets:
    # Setting-69-ASP.meetingdetail_aspx.gridMain.SortExpression=Sequence ASC; Setting-69-Calendar Options=info|; Setting-69-Calendar Year=Next Month; Setting-69-Calendar Body=All; Setting-69-ASP.calendar_aspx.gridCalendar.SortExpression=MeetingStartDate DESC; ASP.NET_SessionId=tmk5pfksowfid2t3nqjmpvac; BIGipServerprod_insite_443=874644234.47873.0000
    # but with any luck, 'Next Month' is the only one that's actually needed.
    # This has to be done before reading the default page,
    # to match the decreasing date order of the meetings on each month's page.
    if now.day > 20:
        cookiedict = { 'Setting-69-Calendar Year': 'Next Month' }
        r = requests.get(MEETING_LIST_URL, cookies=cookiedict)
        parse_html_meeting_list(r.text, only_future)

    # Get the meetings on the default (this month) page.
    # These will be appended to the global list upcoming_meetings.
    r = requests.get(MEETING_LIST_URL, timeout=30)
    parse_html_meeting_list(r.text, only_future)

    # The meeting list is in date/time order, latest first.
    # Better to list them in the other order, starting with
    # meetings today, then meetings tomorrow, etc.
    # That's why we couldn't just write meetings from the earlier loop.
    # Could sort by keys, 'Meeting Date' and 'Meeting Time',
    # but since it's already sorted, it's easier just to reverse.
    upcoming_meetings.reverse()


def parse_html_meeting_list(page_html, only_future=False):
    """Parse the page listing meetings, which is HTML generated by pdftohtml.
       Return a list of dictionaries for each meeting.
       If only_future is set, don't include past meetings.
    """
    soup = BeautifulSoup(page_html, 'lxml')

    # Remove a bunch of spurious tags
    for badtag in [ "font", "span", "div" ]:
        badtags = soup.find_all(badtag)
        for tag in badtags:
            tag.replace_with_children()

    caltbl = soup.find("table",
                       id="ctl00_ContentPlaceHolder1_gridCalendar_ctl00")

    # The legend is in the thead
    fieldnames = []
    for i, field in enumerate(caltbl.thead.find_all("th")):
        if field.text:
            fieldnames.append(field.text.strip())
        else:
            fieldnames.append(str(i))

    # Loop over meetings, rows in the table:
    for row in caltbl.tbody.find_all("tr"):
        dic = {}
        # Loop over columns describing this meeting:
        for i, field in enumerate(row.find_all("td")):
            if fieldnames[i].startswith("Agenda"):
                # If there's an Agenda URL, make it absolute.
                a = field.find("a")
                href = a.get("href")
                if href:
                    dic[fieldnames[i]] = urljoin(MEETING_LIST_URL, href)
                else:
                    dic[fieldnames[i]] = None

            elif fieldnames[i] == 'Meeting Location':
                # The Location field has simple formatting
                # such as <br>, so can't just take .text, alas.
                dic[fieldnames[i]] = ' '.join([str(c).strip()
                                               for c in field.contents]) \
                                        .strip()

            # The little calendar icon somehow comes out with a name of '2'.
            # Skip it.
            elif fieldnames[i] == '2' or not fieldnames[i]:
                continue

            # Most fields are simple and won't have any formatting.
            # They are full of nbsps '\u00a0', though.
            else:
                dic[fieldnames[i]] = field.text.replace('\u00a0', ' ').strip()

        if "Meeting Date" in dic:
            mtg_datetime = meeting_datetime(dic)
            if mtg_datetime and only_future and mtg_datetime < utcnow:
                continue

        upcoming_meetings.append(dic)


def meeting_datetime(mtg):
    """Parse the meeting date and time and return an aware local datetime.
       If there's only a date and no time, return a date object.
    """
    # The parsed time is in the local time and is unaware,
    # because strptime can't create a timezone aware object
    # even if the string it's parsing includes a timezone (see above).
    if "Meeting Time" not in mtg or not mtg["Meeting Time"]:
        mtg["Meeting Time"] = NO_TIME
    try:
        if mtg["Meeting Time"] != NO_TIME:
            unaware = datetime.datetime.strptime(mtg["Meeting Date"] + " "
                                                 + mtg["Meeting Time"],
                                                 '%m/%d/%Y %I:%M %p')
        else:    # No time, so list it at 23:59
            unaware = datetime.datetime.strptime(mtg["Meeting Date"],
                                                 '%m/%d/%Y')
            unaware.replace(hour=23, minute=59, second=0)

        # Make it aware in localtime
        localtime = unaware.astimezone(localtz)
        return localtime

    except ValueError:
        print("ERROR: Can't parse date on meeting:", mtg)
        return None


def diffhtml(before_html, after_html, title=None):
    """Diffs the two files, and returns an html fragment that wraps
       differences in <ins> or <del> tags, which you can style as desired.
       Returns bytes, not str, because everything else works in bytes
       due to using requests.
    """
    if not title:
        title = "Changed Agenda"

    # lxml.html.htmldiff only accepts strings, not bytes, but these
    # were read in as bytes because that's what comes from requests;
    # so translate them.
    if type(before_html) is bytes:
        before_html = before_html.decode()
    if type(after_html) is bytes:
        after_html = after_html.decode()

    # lxml.html.htmldiff returns fragments, not full documents.
    # So add a header that includes a style for ins and del.
    diff = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<link rel="stylesheet" type="text/css" title="Style" href="meetingstyle.css"/>
</head>

<body>
<h1>%s</h1>
''' % (title, title)

    diff += htmldiff(before_html, after_html)

    diff += "\n</body></html>\n"

    # encode to return bytes.
    return diff.encode()


def agenda_to_html(agendaloc, meetingtime, save_pdf_filename=None):
    """Convert a PDF agenda from legistar,
       returning an HTML str (fitz) or bytes (pdftohtml).
    """
    if 'fitz' in sys.modules:
        print("Using fitz")
        return html_agenda_fitz(agendaloc, meetingtime, save_pdf_filename)

    print("No fitz, using pdftohtml")
    return html_agenda_pdftohtml(agendaloc, meetingtime, save_pdf_filename)


def html_agenda_fitz(agendaloc, meetingtime, save_pdf_filename=None):
    """Use fitz (mupdf's engine) to convert PDF to HTML, returned as a string.
    """
    if not save_pdf_filename:
        save_pdf_filename = "/tmp/tmpagenda.pdf"
    if agendaloc.lower().startswith('http') and ':' in agendaloc:
        r = requests.get(agendaloc, timeout=30)

        with open(save_pdf_filename, "wb") as pdf_fp:
            pdf_fp.write(r.content)
        agendaloc = save_pdf_filename
    elif agendaloc.startswith("file://"):
        agendaloc = agendaloc[7:]
    elif ':' in agendaloc:
        print("Don't understand location", agendaloc, file=sys.stderr)
        return None
    # Now agendaloc should be a filename

    def get_link(block, links):
        """Is there a link over this text block? If so, return the URL,
           else None.

           The rect for a link will typically be a little bigger than the
           rect for the corresponding block.
        """
        for l in links:
            # Find the overlap area between the two rectangles, block and link.
            dx = min(block[2], l['from'].x1) - max (block[0], l['from'].x0)
            dy = min(block[3], l['from'].y1) - max (block[1], l['from'].y0)
            if (dx > 0) and (dy > 0):
                return l['uri']
        return None


    html = """<head>
<link href="meetingstyle.css" rel="stylesheet" title="Style" type="text/css"/>
</head>
<body>
"""
    with fitz.open(agendaloc) as doc:
        started = False
        for page in doc:
            links = page.get_links()

            # wlist = page.get_text("words")
            # This is a list of tuples:
            # (x0, y0, x1, y1, "word", block_no, line_no, word_no)

            blocks = page.get_text("blocks", sort=True)
            # This is a list of tuples:
            # (x0, y0, x1, y1, "lines in the block", block_no, block_type)
            # To get font info as well, use
            # page.get_text("dict", flags=11)["blocks"]
            # which is much more granular

            for block in blocks:
                blocktext = block[4].strip()

                if blocktext.startswith("<image:"):
                    continue

                link = get_link(block, links)
                if not link and blocktext.startswith("https://"):
                    link = blocktext

                # Look for headers
                if block[0] >= HEADER_COL[0] and block[0] <= HEADER_COL[1]:
                    if NUMBER_HEADER_RE.match(blocktext):
                        if not started and blocktext.startswith("1.\n"):
                            started = True
                        blocktext = blocktext.replace('\n', ' ')
                        html += f'<h2 class="highlight">{blocktext}</h2>'

                    elif LETTER_HEADER_RE.match(blocktext):
                        # Letter headers are generally something like
                        # A.\n17018-23\nblah blah blah blah
                        # where there's typically a link over the code (#1).
                        # The blah blah blah may be separated into many lines,
                        # in which case they should be rejoined.
                        # However, in some cases there's just a letter+title
                        # and no link: E. Council Chair Report
                        parts = blocktext.splitlines()
                        if link:
                            html += f'<h3 class="highlight">{parts[0]} <a href="{link}">{parts[1]}</a></h3>'
                        else:
                            html += f'<h3 class="highlight">{parts[0]} {parts[1]}</h3>'
                        if len(parts) > 2:
                            html += "<p>\n" + ' '.join(parts[2:])

                    elif link:
                        html += f'<p><a href="{link}">{blocktext}</a>'
                    else:
                        html += "<p>\n" + blocktext.replace('\n', ' ')

                else:
                    # Something not starting at the left margin.
                    # But it might still have a link, or start with
                    # the FILENO_PAT.
                    m = FILENO_PAT.match(blocktext)
                    if m:
                        if link:
                            html += f'<h3 class="highlight"><a href="{link}">{m.group(1)}</a> {m.group(2)}</h3>'
                        else:
                            html += f'<h3 class="highlight">{blocktext}</h3>'
                    elif link:
                        html += f'<p><a href="{link}">{blocktext}</a>'
                    else:
                        html += "<p>\n" + blocktext

    html += "</body></html>"
    return html


def html_agenda_pdftohtml(agendaloc, meetingtime, save_pdf_filename=None):
    """Convert a PDF agenda to text and/or HTML using pdftohtml,
       then returned cleaned_up bytes (not str).
       save_pdf_filename is for debugging:
       if set, save the PDF there and don't delete it.
       Returns the HTML source as bytes, not str.
    """
    if not save_pdf_filename:
        save_pdf_filename = "/tmp/tmpagenda.pdf"
    if agendaloc.lower().startswith('http') and ':' in agendaloc:
        r = requests.get(agendaloc, timeout=30)

        with open(save_pdf_filename, "wb") as pdf_fp:
            pdf_fp.write(r.content)
        agendaloc = save_pdf_filename
    elif ':' in agendaloc:
        print("Don't understand location", agendaloc, file=sys.stderr)
        return None

    htmlfile = save_pdf_filename + ".html"
    args = [ "pdftohtml", "-c", "-s", "-i", "-noframes",
             # "-enc", "utf-8",
             agendaloc, htmlfile ]
    print("Calling", ' '.join(args))
    subprocess.call(args)

    return clean_up_htmlfile(htmlfile, meetingtime)


def highlight_filenumbers(soup):
    for para in soup.find_all("p"):
        paratext = para.text.strip()

        # Upcoming agenda dates should be headers
        if TICKLER_AGENDA_DATE_PAT.match(paratext):
            # newhdr = soup.new_tag("h2")
            # para.wrap(newhdr)
            para.name = "h2"
            para["class"] = "highlight"

        # If it matches the FILENO_PAT, wrap a header around it
        elif FILENO_PAT.match(paratext):
            para.name = "h3"
            para["class"] = "highlight"

    head = soup.head
    head.append(soup.new_tag('style', type='text/css'))
    head.style.append('.highlight { width: 100%; background-color: #7fb; }')


def add_stylesheet(soup):
    # link to the stylesheet:
    csslink =  soup.new_tag("link")
    csslink.attrs["rel"] = "stylesheet"
    csslink.attrs["type"] = "text/css"
    csslink.attrs["title"] = "Style"
    csslink.attrs["href"] = "meetingstyle.css"
    soup.head.insert(0, csslink)


def clean_up_htmlfile(htmlfile, meetingtime):
    """Clean up the scary HTML written by pdftohtml,
       removing the idiotic dark grey background pdftohtml has hardcoded in,
       the assortment of absolute-positioned styles,
       the new-paragraph-for-each-line, etc.
       Returns bytes, not str.
    """
    with open(htmlfile, 'rb') as htmlfp:
        # The files produced by pdftohtml contain '\240' characters,
        # which are ISO-8859-1 for nbsp.
        # Adding "-enc", "utf-8" doesn't change that.
        # If they aren't decoded, BeautifulSoup will freak out
        # and won't see anything in the file at all.
        html_bytes = htmlfp.read().decode('ISO-8859-1')

    # Make some changes. Primarily,
    # replace the grey background that htmltotext wires in
    soup = BeautifulSoup(html_bytes, "lxml")

    # The <style> tag just contains a long comment. No idea why it's there.
    try:
        soup.head.style.decompose()
    except:
        pass

    body = soup.body

    # Insert the meeting date at the beginning of the body
    h_tag = soup.new_tag("h3")
    soup.body.insert(0, h_tag)
    datetext = NavigableString(meetingtime.strftime("%a %b %d"))
    h_tag.append(datetext)

    # Sometimes pdftohtml mysteriously doesn't work, and gives
    # a basically empty HTML file: everything is using position:absolute
    # and that makes it invisible to BeautifulSoup.
    # This seems to be
    # https://gitlab.freedesktop.org/poppler/poppler/-/issues/417
    # Check for that.
    # If all else fails, htmltotext works to extract the text,
    # and might produce cleaner output anyway.
    # Or there may be some way to get BS to find those
    # <p style="position:absolute" tags that it isn't seeing.
    bodylen = len(body.text.strip())
    if bodylen == 0:
        print("** Yikes! Empty HTML from pdftohtml", htmlfile)
        return html
    elif bodylen < 10:
        print(f"Short! Body text is: '{body.text}'")

    del body["bgcolor"]
    del body["vlink"]
    del body["link"]

    # Remove all the fixed pixel width styles
    for tag in body.find_all('style'):
        tag.decompose()
    for tag in body.find_all('div'):
        del tag["style"]
    for tag in body.find_all('p'):
        del tag["style"]

    # Get rid of the pagination
    pagediv_pat = re.compile('page[0-9]*-div')
    divs = list(body.find_all(id=pagediv_pat))
    for div in divs:
        div.replace_with_children()
    # There are also anchors like <a name="8">\n</a>
    # but they're not really hurting anything.

    # Remove hard line breaks. This is a tough decision:
    # some line breaks help readability, some hurt it.
    # for tag in body.find_all('br'):
    #     tag.decompose()

    # pdftohtml renders each line as a separate paragraph,
    # so joining paragraphs helps readability.
    # Call join_consecutive_tags starting with outer tags and working inward.
    # Do this while the p tags still have classes, so paragraphs of
    # different classes don't get merged.
    join_consecutive_tags(body, 'p')

    join_consecutive_tags(body, 'i')
    join_consecutive_tags(body, 'b')

    # Now don't need the class tags any more, so delete them.
    for tag in body.find_all('p'):
        del tag["class"]

    # Try to identify major headers, to highlight them better.
    header_pat = re.compile('([0-9]+)\.\s*([A-Z \(\)\/,]+)$', flags=re.DOTALL)

    # This doesn't work. I don't know why. find_all(text=pat) works fine
    # in simple test cases, but not on the real files.
    # for b in soup.find_all('b', text=header_pat):

    # Instead, loop over all b tags doing the match explicitly:
    for bold in body.find_all('b'):
        m = re.match(header_pat, bold.get_text().strip())
        if not m:
            continue

        # Can't change text like this
        # b.text = f"## {m.groups(1)}. {m.groups(2)}"

        # but we can change the tag name:
        bold.name = 'h2'

    # Highlight all the file numbers, which helps separate items
    highlight_filenumbers(soup)

    add_stylesheet(soup)
    pretty_html_bytes = soup.prettify(encoding='utf-8')

    # Testing: maybe the above changes removed the body contents?
    # (I think this bug is long since fixed.)
    if not body.text:
        print("**Yikes! The changes to", save_pdf_file,
              "made the HTML empty. Saving original instead.")
        with open(os.path.join(RSS_DIR, save_pdf_filename + "_cleaned.html"),
                  "wb") as savfp:
            savefp.write(pretty_html_bytes)
        return html

    return pretty_html_bytes


def join_consecutive_tags(soup, tagname, add_spaces=False):
    """Join consecutive tags of name tag if they have the same attributes.
       E.g. in <p class="foo">some text</p><p class="foo">different text</p>
       would produce <p class="foo">some text different text</p>
       If add_spaces, will add spaces between tags.
    """
    to_merge = []
    tags = list(soup.find_all(tagname))
    prev = None
    sectionnum_pat = re.compile('[0-9A-Z]{,2}\.')
    for tag in tags:
        prev = tag.find_previous_sibling()

        # If the two tags have the same parent and the same class,
        # they should be merged.
        if prev and prev.attrs == tag.attrs:
            # First merge in the list?
            if not to_merge:
                to_merge.append([prev, tag])
                continue

            else:
                # Should these be merged with the last merge?
                last_group = to_merge[-1]
                last_tag_merged = last_group[-1]
                prev_sib = prev.find_previous_sibling()

                # SPECIAL CASE FOR LEGISTAR:
                # Does it look like a section header?
                # Don't merge a paragraph that looks like "2."
                # with whatever was before it.
                if tag.name == 'p' and re.match(sectionnum_pat, tag.text):
                    continue

                elif (prev == last_tag_merged and
                      tag.attrs == last_tag_merged.attrs):
                    # Continue a group merge of three or more tags
                    last_group.append(tag)
                else:
                    # New pair of mergers, make a new group
                    to_merge.append([prev, tag])
        prev = tag

    for group in to_merge:
        first = group[0]
        for tag in group[1:]:
            # Iterating directly over tag.children gets crossed up
            # when some of the children are moved to another tag.
            children = list(tag.children)
            for child in children:
                first.append(child)
            # All of tag's children have been moved to first.
            # Delete tag.
            tag.decompose()


def get_tickler(agenda_str, meetingtime, tickler_html_file):
    """Does an agenda include a tickler?
       Input can be either a filename or HTML source as a string or bytes.
       If there's a tickler, return full path to the written tickler html,
       else None.
    """
    if not agenda_str:
        return None

    soup = BeautifulSoup(agenda_str, "lxml")
    if not soup:
        print("get_tickler: No soup", file=sys.stderr)
        return None

    # Does it have a tickler?

    tickler_url = None
    for a in soup.find_all("a"):
        if "tickler" in a.text.lower():
            tickler_url = a.get("href")
            break
    else:
        # print("No tickler")
        return None

    # The tickler is another PDF file, natch. Convert it:
    tickler_html = html_agenda_pdftohtml(tickler_url, meetingtime).decode()
    soup = BeautifulSoup(tickler_html, "lxml")

    # First give it a clear title. After html_agenda_pdf2html,
    # there's an h3 at the beginning with the date of the tickler.
    firstheader = soup.find('h3')
    if firstheader:
        headerchild = next(firstheader.children)
        headertext = headerchild.strip()
        if TICKLER_HDR_DATE_PAT.match(headertext):
            firstheader.name = 'h1'
            headerchild.replaceWith("Tickler, " + headertext)
        else:
            print("firstheader didn't match:", firstheader, file=sys.stderr)
    else:
        print("No h3 anywhere in tickler file", file=sys.stderr)

    # The tickler html comes out with no structure at all; you can't even
    # assume that each item has its own <b> tag.
    # XXX Would be nice to separate the separate lines into separate
    # <p>s and <b>s.
    lines = []
    for para in soup.find_all("p"):
        lines = para.text.strip().splitlines()
        if len(lines) > 1:
            # Discussion of depth-first iteration:
            # https://stackoverflow.com/q/4814317
            # Get rid of some of the whitespace-only tags:
            for i, p in enumerate(para.recursiveChildGenerator()):
                if type(p) is NavigableString:
                    if not p.strip():
                        del p

    highlight_filenumbers(soup)

    add_stylesheet(soup)
    pretty_html_bytes = soup.prettify(encoding='utf-8')
    tickler_html_file = os.path.join(RSS_DIR, tickler_html_file)
    with open(tickler_html_file, "wb") as fp:
        fp.write(pretty_html_bytes)
        # print("Wrote tickler to", tickler_html_file, file=sys.stderr)
        os.system("ls -l " + tickler_html_file)

    return tickler_html_file


NO_AGENDA = b"No agenda available."

def write_rss20_file(mtglist):
    """Take a list meeting dictionaries
       and make RSS and HTML files from it.
    """
    active_meetings = []

    ##############
    # Generate index HTML and RSS file headers.
    # Open both the RSS and HTML files:
    outrssfilename = os.path.join(RSS_DIR, "index.rss")
    outhtmlfilename = os.path.join(RSS_DIR, "index.html")
    with open(outrssfilename, 'w') as rssfp, \
         open(outhtmlfilename, 'w') as htmlfp:

        print("\n==== Generating RSS for", len(mtglist), "meetings")

        gendate = now.strftime(RSS_DATE_FORMAT)
        print(f"""<?xml version="1.0" encoding="iso-8859-1" ?>
<rss version="2.0"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

<channel>
   <title>Los Alamos County Government Meetings</title>
   <link>{RSS_URL}losalamosmeetings</link>
   <description>An Unofficial, Non-Sanctioned Listing of Los Alamos Government Meetings, provided by Akkana Peck.</description>
   <language>en</language>
   <copyright>Public Domain</copyright>
   <ttl>14</ttl>
   <pubDate>{gendate}</pubDate>
   <managingEditor>akk at shallowsky dot com (Akkana Peck)</managingEditor>
   <generator>losalamosmtgs</generator>
""",
              file=rssfp)

        print(f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">

<html>
<head>
  <title>Los Alamos County Government Meetings</title>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="alternate" type="application/rss+xml"
        title="Los Alamos Meetings Feed"
        href="{RSS_URL}index.rss" />
  <link rel="stylesheet" type="text/css" title="Style" href="meetingstyle.css"/>
</head>
<body>
<h1>Los Alamos County Government Meetings</h1>
As of: {gendate}
 ... <a href="about.html">About Los Alamos Meetings (How to Use This Page)</a>
 ... <a href="{RSS_URL}index.rss">Los Alamos Meetings RSS2.0 Feed</a>.

""", file=htmlfp)

        agendafile = None
        agenda_html = None
        meetingtime = None

        for mtg in mtglist:
            # Did the previous meeting have a tickler?
            # Only applicable for County Council meetings
            # agendafile = os.path.join(RSS_DIR, cleanname + ".html")
            if agendafile and agenda_html and "CountyCouncil" in agendafile:
                print("Just finished a council meeting, looking for a tickler",
                      file=sys.stderr)
                meetingtimestr = meetingtime.strftime("%Y-%m-%d")
                tickler_filename = meetingtimestr + "-Tickler.html"
                tickler_filepath = os.path.join(RSS_DIR, tickler_filename)
                tickler_filepath = get_tickler(agenda_html, meetingtime,
                                               tickler_filename)
                desc = f"County Council Tickler for {meetingtimestr}"
                lastmod = datetime.datetime.now()
                guid = tickler_filename
                url = f"{RSS_URL}{tickler_filename}"

                # Add to the RSS
                if tickler_filepath:
                    active_meetings.append(tickler_filename)
                    print(f"""<item>
   <title>{desc}</title>
   <guid isPermaLink="false">{guid}</guid>
   <link>{url}</link>
   <description><![CDATA[ {desc} ]]>
   </description>
   <pubDate>{lastmod}</pubDate>
</item>""",
                          file=rssfp)

                    # Add to the HTML
                    print(f"""<h2>{desc}</h2>
<p>
<a href="{tickler_filename}">{desc}</a>
<p>(Last modified: {lastmod}.)
""",
                          file=htmlfp)

            # Is the meeting in the future? Don't list past meetings.
            meetingtime = meeting_datetime(mtg)
            if not meetingtime:
                print("Skipping", mtg["Name"], mtg["Meeting Date"],
                      "because of bad meeting datetime",
                      mtg["Meeting Date"], mtg["Meeting Date"])
                continue
            if meetingtime < now:
                print("Skipping", mtg["Name"], mtg["Meeting Date"],
                      "because", meetingtime, "<", now)
                continue

            lastmod = None
            mtg['cleanname'] = mtgdic_to_cleanname(mtg)
            cleanname = mtg['cleanname']
            print("\n====", cleanname)

            if mtg["Agenda"]:      # There is an agenda URL listed
                print(cleanname, "has an agenda: fetching it")
                # XXX TEMPORARY: save the PDF filename, because sometimes
                # pdftohtml produces an HTML file with no content even
                # though there's content in the PDF.
                pdfout = os.path.join(RSS_DIR, cleanname + ".pdf")
                try:
                    agenda_html = agenda_to_html(mtg["Agenda"],
                                                 meetingtime,
                                                 save_pdf_filename=pdfout)
                except ReadTimeoutError:
                    print("Timed out on " + agendaloc)
                    agenda_html = NO_AGENDA
                    agendastatus = "timeout"
            else:                   # No previous agenda
                print(cleanname, "has no agenda to fetch")
                agenda_html = NO_AGENDA
            # Now agenda_html is guaranteed to be set, either way.

            # Might need a diff file too:
            agenda_diff = None

            # Does the agenda file need to be (re)written?
            write_agenda_file = False

            # See if there was already an agenda file left from previous runs:
            agendafile = os.path.join(RSS_DIR, cleanname + ".html")
            # print("agenda filename", agendafile)

            try:
                with open(agendafile, "rb") as oldfp:
                    oldhtml = oldfp.read()

                if NO_AGENDA in oldhtml:         # no agenda previously
                    if Verbose:
                        print("No agenda previously")
                    if agenda_html != NO_AGENDA: # but there is now
                        write_agenda_file = True
                        agendastatus = "new"
                        print(cleanname, ": new agenda")
                    else:
                        agendastatus = "no"
                        print(cleanname, ": no agenda")

                else:                            # there was a previous agenda
                    if Verbose:
                        print("There was a previous agenda: ===============")
                    if agenda_html == NO_AGENDA:
                        print(oldhtml)
                        print("========= but now, ===============")
                        print(agenda_html)

                        if not agendastatus:
                            agendastatus = "removed"
                        print(cleanname, ": removed agenda")

                        # don't write over the old agenda file
                        write_agenda_file = False

                    elif agenda_html != oldhtml:  # changed agenda
                        write_agenda_file = True

                        # XXX TEMPORARY: save the previous file,
                        # to have them available while debugging diffs.
                        os.rename(agendafile,
                                  os.path.join(RSS_DIR,
                                               cleanname + "-old.html"))
                        # End temporary clause

                        # Since the agenda has changed, make a diff file
                        # highlighting the parts that changed.
                        agenda_diff = diffhtml(oldhtml, agenda_html,
                                               title=cleanname)
                        agenda_diff_file = os.path.join(RSS_DIR,
                                            mtg['cleanname'] + "-diff.html")
                        with open(agenda_diff_file, 'wb') as difffp:
                            difffp.write(agenda_diff)

                        agendastatus = "changed"
                        print(cleanname, ": changed agenda")
                    else:
                        agendastatus = "unchanged"
                        print(cleanname, ": unchanged agenda")

            except FileNotFoundError:
                # No agenda file there previously; probably a new meeting
                if Verbose:
                    print("No previous agenda file")
                write_agenda_file = True
                if agenda_html == NO_AGENDA:
                    if Verbose:
                        print("... and no new agenda now")
                    agendastatus = "no"
                else:
                    if Verbose:
                        print("but there's an agenda there")
                    agendastatus = "new"

            # Now agenda_html and agendastatus should be set,
            # and maybe agenda_diff too.

            # Write the agenda file if it's changed:
            if write_agenda_file:
                if type(agenda_html) is bytes:
                    with open(agendafile, 'wb') as outfp:
                        outfp.write(agenda_html)
                elif type(agenda_html) is str:
                    with open(agendafile, 'w') as outfp:
                        outfp.write(agenda_html)
                else:
                    print("Internal error: agenda_html is type",
                          type(agenda_html), file=sys.stderr)
                    continue

            # Either way, this meeting is still listed:
            # note it so it won't be cleaned from the directory.
            active_meetings.append(cleanname)

            # Get the old JSON
            changestr = ""
            jsonfile = os.path.join(RSS_DIR, mtg['cleanname'] + ".json")
            try:
                with open(jsonfile) as jsonfp:
                    oldmtg = json.loads(jsonfp.read())

                # mtg doesn't have lastmod, so to make sure that
                # doesn't trigger a change, copy it:
                mtg['lastmod'] = oldmtg['lastmod']

                changed_keys = {key for key in oldmtg.keys() & mtg
                                if oldmtg[key] != mtg[key]}
                if changed_keys:
                    lastmod = now
                    changestr = "<p>Changed: " + ', '.join(changed_keys) \
                        + "</p>"
                    print("Keys changed:", changed_keys, "lastmod is", lastmod)

                elif not lastmod:
                    print("Nothing has changed, keeping lastmod")
                    lastmod = datetime.datetime.strptime(oldmtg['lastmod'],
                                                         RSS_DATE_FORMAT)
            except (RuntimeError, OSError) as e:
                if os.path.exists(jsonfile):
                    print("Error reading jsonfile: %s" % e)
                    changestr += "Error reading jsonfile: %s\n<p>" % e
                elif Verbose:
                    print("No JSON file there previously")
                lastmod = now
                changestr += "<b>New listing.</b>\n<p>"

            # Update to the real lastmod date before writing JSON
            mtg['lastmod'] = lastmod.strftime(RSS_DATE_FORMAT)
            mtg['GUID'] = cleanname + '.' + lastmod.strftime("%Y%m%d-%H%M")

            # If the meeting is new or something has changed,
            # (re)write the JSON file..
            with open(jsonfile, 'w') as jsonfp:
                jsonfp.write(json.dumps(mtg, indent=4))

            mtgtitle = f"""{mtg['Name']} on {meetingtime.strftime("%a %b %d")}"""

            desc = f"""{mtg['Name']}: {mtg['Meeting Date']} at {mtg['Meeting Time']}<br />
"""

            # Set up the change strings for the header and body
            if agendastatus == "new":
                agenda_hdr = " (AGENDA)"
                desc += "<p><b>There is a new agenda.</b>"
            elif agendastatus == "removed":
                agenda_hdr = " (REMOVED AGENDA)"
                desc += "<p><b>The agenda has been removed.</b>"
            elif agendastatus == "changed":
                agenda_hdr = " (CHANGED AGENDA)"
                desc += "<p><b>The agenda has changed.</b>"
            elif agendastatus == "unchanged":
                agenda_hdr = ""
                desc += "<p>The agenda hasn't changed."
            elif agendastatus == "no":
                agenda_hdr = " (no agenda)"
                desc += "<p>No agenda yet."

            if mtg['Meeting Location']:
                desc += "<p>Location:" + mtg['Meeting Location']

            if changestr:
                desc += "<p>" + changestr + '\n'

            if agenda_diff:
                link = f"{RSS_URL}{cleanname}-diff.html"
            else:
                link = f"{RSS_URL}{cleanname}.html"

            if mtg["Agenda"]:
                desc = f"""{desc}<p>
<a href="{mtg["Agenda"]}">Agenda PDF</a><br>
</p>
"""

            if mtg["Agenda Packets"]:
                # The agenda packet links tend to have & in them
                # and so need to be escaped with CDATA
                if 'http' in mtg["Agenda Packets"]:
                    desc += f"""<p><a href="{mtg["Agenda Packets"]}">Agenda Packet</a></p>\n"""
                else:
                    desc = f"""<p>Agenda packet: {mtg["Agenda Packets"]}</p>\n"""

            print("GUID will be", mtg['GUID'], "lastmod is", mtg['lastmod'])

            # Add the item to the RSS
            print(f"""<item>
   <title>{mtgtitle} {agenda_hdr}</title>
   <guid isPermaLink="false">{mtg['GUID']}</guid>
   <link>{link}</link>
   <description><![CDATA[ {desc} ]]>
   </description>
   <pubDate>{mtg['lastmod']}</pubDate>
</item>""", file=rssfp)

            # And add it to the HTML
            print(f"<p><h2>{mtgtitle} {agenda_hdr}</h2>", file=htmlfp)
            if mtg["Agenda"]:
                print(f'<p><b><a href="{link}">Agenda: {mtgtitle}</a></b>',
                      file=htmlfp)
            # else:
            #     print("<p>No agenda yet", file=htmlfp)
            print(f"""<p>
{desc}
<p>(Last modified: {gendate}.)
""",
                  file=htmlfp)


        print("</channel>\n</rss>", file=rssfp)
        print("</body></html>", file=htmlfp)

    print("Wrote", outrssfilename, "and", outhtmlfilename)

    # Remove obsolete files for meetings no longer listed.
    for f in os.listdir(RSS_DIR):
        # Only clean up certain extensions:
        rmexts = [ '.json', '.rss', '.html', '.pdf' ]
        name, ext = os.path.splitext(f)
        if ext not in rmexts:
            continue

        # Protected files
        if f.startswith("index") or f.startswith("about"):
            continue

        def is_active(f):
            for act in active_meetings:
                if f.startswith(act):
                    return True
            return False

        if not is_active(f):
            print("removing", f)
            os.unlink(os.path.join(RSS_DIR, f))


VALID_FILENAME_CHARS = "-_." + string.ascii_letters + string.digits

def clean_filename(badstr):
    return ''.join(c for c in badstr if c in VALID_FILENAME_CHARS)


def mtgdic_to_cleanname(mtgdic):
    """A standard way to turn date and committee name into something
       that can be used for filenames or URLs.
       Will be used both for the agenda file and for RSS entries.
    """
    mtg_dt = meeting_datetime(mtgdic)
    if mtg_dt:
        return mtg_dt.strftime("%Y-%m-%d") + '-' \
            + clean_filename(mtgdic["Name"])
    return "notime-" + clean_filename(mtgdic["Name"])


if __name__ == '__main__':
    if len(sys.argv) > 1:
        RSS_DIR = sys.argv[1]

        RSS_URL = sys.argv[2]
        # RSS_URL is a directory and must end with a slash
        if not RSS_URL.endswith('/'):
            RSS_URL += '/'

    build_upcoming_meetings_list()

    write_rss20_file(upcoming_meetings)

