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
import time
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
# But it doesn't seem to work as well as pdftohtml anyway.
# try:
#     import fitz
# except:
#     print("No PyMuPDF installed, using pdftohtml")


########## CONFIGURATION ##############
# You can also pass in RSS_URL RSS_DIR as two optional arguments

# Where to start: the public legistar meeting list
MEETING_LIST_URL = "https://losalamos.legistar.com/Calendar.aspx"

# The place where the RSS will be hosted. Must end with a slash.
# The RSS file will be this/index.rss.
RSS_URL = "https://localhost/los-alamos-meetings/"

# Where to put the generated RSS file. Customize this for your website.
RSS_DIR = os.path.expanduser("~/web/los-alamos-meetings")
if not os.path.exists(RSS_DIR):
    os.makedirs(RSS_DIR)

# Directory to store long-term records (CSV) of agenda items vs. dates.
# If None, long-term records will not be stored.
AGENDA_ITEM_STORE = os.path.join(RSS_DIR, "AgendaItems")

######## END CONFIGURATION ############

RECORDS_FILEBASE = 'meeting-records.html'


# Make a timezone-aware datetime for now:
now = datetime.datetime.now().astimezone()
localtz = now.tzinfo

today = now.date()
todaystr = today.strftime("%Y-%m-%d")

# and a UTC version
utcnow = datetime.datetime.now(tz=datetime.timezone.utc)

# Needed to deal with meetings that don't list a time:
NO_TIME = "NO TIME"

# Something guaranteed to be before any meetings.
# Can't use datetime.datetime.min because it needs to be tz-aware.
EARLY_DATETIME = datetime.datetime(1970, 1, 1).astimezone()
EARLY_DATE = EARLY_DATETIME.date()


Verbose = True

# and save the timezone
localtz = now.tzinfo

# Format for dates in RSS:
# This has to be GMT, not %Z, because datetime.strptime just
# throws away any %Z info anyway rather than parsing it.
# Better to get an error if we see any time that's not GMT.
RSS_DATE_FORMAT = "%a, %d %b %Y %H:%M GMT"

# Match the date format used in the tickler, e.g. Tue Feb 28
TICKLER_HDR_DATE_PAT = re.compile("[MTWFS][a-z]{2} [A-Z][a-z]{2} [0-9]{1,2}")

# Items are introduced with a "file number" which can help separate them
# in what otherwise looks like a sea of text.
FILENO_PAT = re.compile('[A-Z0-9]{2,}-[A-Z0-9]{2,}')

# What to search for when linkifying.
# Note: this doesn't always get the whole link, but that's not the fault
# of LINK_PAT; it's that sometimes the PDFs split the URL across
# several lines.
LINK_PAT = re.compile('^https://')

# A few other patterns that are used here and there
sectionnum_pat = re.compile(r'[0-9A-Z]{,2}\.')
pagediv_pat = re.compile('page[0-9]*-div')
header_pat = re.compile(r'([0-9]+)\.\s*([A-Z \(\)\/,]+)$', flags=re.DOTALL)


# Where temp files will be created. pdftohtml can only write to a file.
tempdir = tempfile.mkdtemp()

#
# Meeting Records (Minutes, Video, Audio):
# Records are stored in a JSON file records.json
# Each record has the date it was first seen.
# It may also include a URL, but the URL is bogus:
# unfortunately Legistar doesn't offer externally-viable links,
# so the audio and video links they show on the calendar page
# just go back to the calendar page, while the links for minutes
# go to the agenda page instead.
#
# Sadly, the links in the Legistar audio/video are completely
# bogus and just go back to the Legistar calendar;
# there's no way to link directly to the Video or Audio.
# Even worse, you can't even link to the correct month
# where someone might find the transcript: they have to
# load the calendar and then figure out how to navigate to
# the correct month, which will then screw them up the next
# time they want to load the calendar.
# ARGHHH!
#
# Clients need easy access both by cleanname and by date.
# Dates are yyyy-mm-dd strings.
#
class MeetingRecords:
    # Types of records of meetings (to match the legistar calendar page):
    RECORD_TYPES = [ 'Minutes', 'Video', 'Audio', "Updated" ]

    RECORDFILENAME = "records.json"

    def __init__(self):
        # record_dic is indexed by cleanname, and consists of
        # a list of dictionaries of { record_type: (date, url) }
        # Each cleanname also has a latest-record date.
        self.record_dic = {}

    def add_meeting(self, mtg_dic):
        # print("add_meeting from:", mtg_dic['cleanname'])
        for rtype in self.RECORD_TYPES:
            if rtype in mtg_dic and mtg_dic[rtype]:
                self.add_record(mtg_dic['cleanname'], rtype, mtg_dic[rtype])

    def add_record(self, cleanname, record_type, url):
        """Add a record of one type for one meeting.
           If the indicated meeting already has that record type,
           don't update anything, else set the date to today's date.
        """
        if cleanname not in self.record_dic or \
           record_type not in self.record_dic[cleanname] or \
           self.record_dic[cleanname][record_type][0] != url:

            if cleanname not in self.record_dic:
                self.record_dic[cleanname] = { 'name': cleanname }

            self.record_dic[cleanname][record_type] = (url, todaystr)
            self.record_dic[cleanname]['latest-record'] = todaystr
            # Only need to add name if there's been at least one record

    def new_records_today(self):
        """An iterator that returns dicts of meetings that had
           at least one new record appear today.
        """
        for name in self.record_dic:
            if self.record_dic[name]['latest-record'] == todaystr:
                yield self.record_dic[name]
            # else:
            #     print(name, "has older date,",
            #           self.record_dic[name]['latest-record'])

    def records_by_date(self):
        """An iterator yielding dicts, sorted by latest record date.
           starting with the most recent.
        """
        # The bydate list is a list of (cleanname, date) sorted by date,
        # most recent first.
        bydate_list = []
        for name in self.record_dic:
            bydate_list.append(( name, self.record_dic[name]['latest-record'] ))

        bydate_list.sort(key=lambda t: t[1], reverse=True)

        for name, lastmod in bydate_list:
            yield self.record_dic[name]

    def read_file(self):
        try:
            with open(os.path.join(RSS_DIR, self.RECORDFILENAME)) as fp:
                self.record_dic = json.load(fp)
        except:
            if not self.record_dic and Verbose:
                print("No records saved from last time")

    def save_file(self):
        """Clean and save the records.json file.
        """
        # Don't keep anything older than 15 days.
        keys = list(self.record_dic.keys())
        for key in keys:
            recdate = datetime.datetime.strptime(
                self.record_dic[key]["latest-record"], "%Y-%m-%d").date()
            if (today - recdate).days > 15:
                del self.record_dic[key]

        # Now save it
        with open(os.path.join(RSS_DIR, self.RECORDFILENAME), 'w') as fp:
            json.dump(self.record_dic, fp, indent=4)
            # XXX Would be nice to save them in sorted order
        print("Saved records to", os.path.join(RSS_DIR, self.RECORDFILENAME))


mtg_records = MeetingRecords()

upcoming_meetings = []


def build_upcoming_meetings_list():
    # Initialize MeetingRecords from the saved file.
    mtg_records.read_file()

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
        parse_html_meeting_list(r.text)

    # Get the meetings on the default (this month) page.
    # These will be appended to the global list upcoming_meetings.
    r = requests.get(MEETING_LIST_URL, timeout=30)
    parse_html_meeting_list(r.text)

    # Look at last month to get any new records that have been posted
    cookiedict = { 'Setting-69-Calendar Year': 'Last Month' }
    r = requests.get(MEETING_LIST_URL, cookies=cookiedict)
    parse_html_meeting_list(r.text)

    # Now that all relevant months have been read,
    # it's safe to save the records file.
    mtg_records.save_file()

    # The meeting list is in date/time order, latest first.
    # Better to list them in the other order, starting with
    # meetings today, then meetings tomorrow, etc.
    # That's why we couldn't just write meetings from the earlier loop.
    # Could sort by keys, 'Meeting Date' and 'Meeting Time',
    # but since it's already sorted, it's easier just to reverse.
    upcoming_meetings.reverse()


def parse_html_meeting_list(page_html):
    """Parse the page listing meetings, which is HTML generated by pdftohtml.
       Return a list of dictionaries for each meeting.
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
        mtg = {}
        # Loop over columns describing this meeting:
        for i, cell in enumerate(row.find_all("td")):
            if fieldnames[i].startswith("Agenda"):
                # If there's an Agenda URL, make it absolute.
                a = cell.find("a")
                href = a.get("href")
                if href:
                    mtg[fieldnames[i]] = urljoin(MEETING_LIST_URL, href)
                else:
                    mtg[fieldnames[i]] = None

            elif fieldnames[i] == 'Meeting Location':
                # The Location field has simple formatting
                # such as <br>, so can't just take .text, alas.
                mtg[fieldnames[i]] = ' '.join([str(c).strip()
                                               for c in cell.contents]) \
                                        .strip()

            # The little calendar icon somehow comes out with a name of '2'.
            # Skip it.
            elif fieldnames[i] == '2' or not fieldnames[i]:
                continue

            # Minutes/Video/Audio: save the URL, if any, else None
            # XXX Though the URL is actually meaningless and doesn't work,
            # so consider changing this to not store it.
            elif fieldnames[i] in MeetingRecords.RECORD_TYPES:
                # print(mtg["Name"], "record type", fieldnames[i])
                try:
                    # Legistar uses \xa0 instead of spaces
                    fieldtext = cell.text.replace('\u00a0', ' ').strip()
                    assert fieldtext != "Not available"
                    # print("Not not available")
                    # In case they start playing other games with characters,
                    # check the href too:
                    href = a.get("href")
                    hclass = a.get("class")
                    # Real video links don't have a class, but
                    # "Not available" has fake links with a class.
                    if hclass:
                        assert 'NotAvailable' not in hclass
                        # But Legistar misspells it:
                        assert 'NotAvailble' not in hclass
                    # print("Real href")
                    mtg[fieldnames[i]] = urljoin(MEETING_LIST_URL, href)
                    # print("  Set link to", mtg[fieldnames[i]])
                except AssertionError:
                    mtg[fieldnames[i]] = None

            # Most cells are simple and won't have any formatting.
            # They are full of nbsps '\u00a0', though.
            else:
                val = cell.text.replace('\u00a0', ' ').strip()
                # if fieldnames[i] == "Name":
                #     print("--", val)
                if val:
                    mtg[fieldnames[i]] = val

        mtg['cleanname'] = mtgdic_to_cleanname(mtg)
        mtg_records.add_meeting(mtg)

        # Now we have a good mtg dictionary.
        # If it's in the future, save it in upcoming_meetings;
        # if the past, save it in past_records if it has records.
        meetingdate = meeting_datetime(mtg).date()
        if meetingdate >= today:
            upcoming_meetings.append(mtg)


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


def html_head(title):
    return f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">

<html>
<head>
  <title>{ title }</title>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="alternate" type="application/rss+xml"
        title="Los Alamos Meetings Feed"
        href="{RSS_URL}index.rss" />
  <link rel="stylesheet" type="text/css" title="Style" href="meetingstyle.css"/>
</head>
<body>
<h1>{ title }</h1>"""


def rss_entry(title, desc, guid, url, lastmod):
    # lastmod must be in RSS_DATE_FORMAT
    # url will be made absolute
    if ':' not in url:
        url = RSS_URL + url
    return f"""<item>
   <title>{title}</title>
   <guid isPermaLink="false">{guid}</guid>
   <link>{url}</link>
   <description><![CDATA[ {desc} ]]>
   </description>
   <pubDate>{lastmod}</pubDate>
</item>"""


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
    diff = html_head(title)

    diff += htmldiff(before_html, after_html)

    diff += "\n</body></html>\n"

    # encode to return bytes.
    return diff.encode()


def agenda_to_html(mtg, meetingtime, save_pdf_filename=None):
    if save_pdf_filename:
        prettyname = os.path.basename(save_pdf_filename)
    else:
        prettyname = agendaloc
    print("Converting agenda for", prettyname, file=sys.stderr)
    if 'fitz' in sys.modules:
        print("Using fitz")
        return html_agenda_fitz(mtg, meetingtime, save_pdf_filename)

    # print("No fitz, using pdftohtml")
    return html_agenda_pdftohtml(mtg, meetingtime, save_pdf_filename)


def html_agenda_fitz(mtg, meetingtime, save_pdf_filename=None):
    """Use fitz (mupdf's engine) to convert PDF to HTML, returned as a string.
    """
    agendaloc = mtg["Agenda"]
    doc = fitz.open(agendaloc)

    def find_indent_levels(pdfdoc):
        indents = []
        for page in pdfdoc.pages():
            for block in page.get_text("blocks"):
                indent = round(block[0])
                if indent not in indents:
                    indents.append(indent)
        indents.sort()

        def group_clusters(lis, max_sep):
            """Reduce a list of numbers removing numbers that are
               close to each other.
               E.g. [1, 2, 3, 44, 46] -> [2, 45].
               lis is a sorted list of numbers.
               max_sep is the maximum separation allowed.
            """
            # clusters is a list of [ (low, high) ]
            clusters = []
            def add_to_clusters(l):
                for c in clusters:
                    if l >= c[0] and l <= c[1]:
                        # the value is already represented by this cluster
                        return
                    # Okay, l is outside this cluster. But is it close?
                    # On the low end?
                    if l <= c[1] and l >= c[1] - max_sep:
                        c[0] = l
                        return
                    # Or on the high end?
                    if l >= c[0] and l <= c[0] + max_sep:
                        c[1] = l
                        return
                # It's outside all of the known ranges.
                # Add a new range.
                clusters.append([l, l])

            for l in lis:
                add_to_clusters(l)

            # Now clusters is a list of ranges. Take the average of each.
            return [ int((c[0] + c[1])/2.) for c in clusters ]

        return group_clusters(indents, 10)

    indent_levels = find_indent_levels(doc)
    # print("Found indent levels:", indent_levels)

    html = """<html>
<body>
<h3>%s</h3>
""" % (meetingtime.strftime("%a %y-%m-%d"))
    for page in doc.pages():
        # blocks are like paragraphs in a normal PDF. Here, ??
        # block is supposedly a tuple,
        #   (x0, y0, x1, y1, "lines in block", block_type, block_no)
        # according to https://pymupdf.readthedocs.io/en/latest/app2.html
        # but I think the last two are reversed, it's really no, type.
        # flags=0 disables images, but might also disable other
        # desirable things, so watch out.
        # https://pymupdf.readthedocs.io/en/latest/app2.html#text-extraction-flags
        # values include TEXT_PRESERVE_IMAGES, TEXT_PRESERVE_LIGATURES,
        # TEXT_PRESERVE_SPANS, TEXT_PRESERVE_WHITESPACE.
        blocks = page.get_text("blocks", flags=0)

        for b in blocks:
            # This clause isn't needed if TEXT_PRESERVE_IMAGES isn't set.
            # if b[4].startswith("<image:"):
            #     print("Skipping an image")
            #     continue

            # Is the indent close to the minimum indent?
            # Then it's a header.
            # Decide which level of header to use based on content.
            if isclose(b[0], indent_levels[0], abs_tol=10):
                # print("HEADER:", b[4].replace('\n', ' '))
                if re.match(r'[0-9]+\.\n', b[4]):
                    html += "<h1>%s</h1>\n<p>\n" % b[4]
                elif re.match(r'[A-Z]+\.\n', b[4]):
                    html += "<h2>%s</h2>\n<p>\n" % b[4]
                else:
                    html += "<p>%s</p>" % b[4]

            elif isclose(b[0], indent_levels[1], abs_tol=10):
                # print("    ", b[4].replace('\n', ' '))
                html += "<br>\n%s\n" % b[4]
            else:
                # print("        OTHER INDENT:", b[4].replace('\n', ' '))
                html += "<br><blockquote>\n%s</blockquote>\n" % b[4]

    html += "</body></html>"
    return html


def html_agenda_pdftohtml(mtg, meetingtime, save_pdf_filename=None, url=None):
    """Convert a PDF agenda to text and/or HTML using pdftohtml,
       then returned cleaned_up bytes (not str).
       save_pdf_filename is for debugging:
       if set, save the PDF there and don't delete it.
       Returns the HTML source as bytes, not str.
    """
    if url:
        agendaloc = url
    else:
        agendaloc = mtg["Agenda"]
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
    print("Calling", ' '.join(args), file=sys.stderr)
    subprocess.call(args)

    return clean_up_htmlfile(htmlfile, mtg, meetingtime)


def highlight_filenumbers(soup):
    """Find agenda items, which match FILENO_PAT and contain a link
       to related documents on Legistar.
       Highlight them with h3.highlight,
       and return a list of dicts with 'href' and 'desc'
       that can be saved to the item store.
    """
    item_list = []

    for para in soup.find_all("p"):
        # If it matches the FILENO_PAT, change the p tag to an h3 highlight.
        if FILENO_PAT.match(para.text.strip()):
            # para.wrap(soup.new_tag("h3"))
            para.name = "h3"
            para["class"] = "highlight"

        # Get the link, if any
        try:
            href = para.find('a').attrs['href']
        except:
            href = None

        if para.name == 'h3':
            # Look forward to the next paragraph, which is the description
            # of the item.
            nextpara = para.find_next('p')
            if nextpara:
                # Legistar likes to use \xa0, non-breaking spaces
                # so sub them out first before replacing runs of whitespace
                desctext = re.sub(r'\s{2,}', ' ',
                                  nextpara.text.strip().replace('\xa0', ' '))
                item_list.append({ 'url': href, 'itemdesc': desctext })
            else:
                print("Couldn't find next paragraph after h3", para)

    head = soup.head
    head.append(soup.new_tag('style', type='text/css'))
    head.style.append('.highlight { width: 100%; background-color: #7fb; }')

    return item_list


def add_stylesheet(soup):
    # link to the stylesheet:
    csslink =  soup.new_tag("link")
    csslink.attrs["rel"] = "stylesheet"
    csslink.attrs["type"] = "text/css"
    csslink.attrs["title"] = "Style"
    csslink.attrs["href"] = "meetingstyle.css"
    soup.head.insert(0, csslink)


def clean_up_htmlfile(htmlfile, mtg, meetingtime):
    """Clean up the scary HTML written by pdftohtml,
       removing the idiotic dark grey background pdftohtml has hardcoded in,
       the assortment of absolute-positioned styles,
       the new-paragraph-for-each-line, etc.
       Also, try to linkify links, identify sections, save agenda items, etc.
       Returns bytes, not str.
    """
    global AGENDA_ITEM_STORE

    with open(htmlfile, 'rb') as htmlfp:
        # The files produced by pdftohtml contain '\240' characters,
        # which are ISO-8859-1 for nbsp.
        # Adding "-enc", "utf-8" doesn't change that.
        # If they aren't decoded, BeautifulSoup will freak out
        # and won't see anything in the file at all.
        html_bytes = htmlfp.read().decode('ISO-8859-1')

    # Make some changes to make the HTML readable and parseable.
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
    # to make the HTML more readable.
    item_list = highlight_filenumbers(soup)

    # Write agenda items found by highlight_filenumbers to the item store,
    # if there is one.
    # XXX need a way to avoid duplicates when meetings are re-posted

    # Create the agenda item store directory if not already there
    if item_list and AGENDA_ITEM_STORE:
        try:
            os.mkdir(AGENDA_ITEM_STORE)
        except FileExistsError:
            pass
        except Exception as e:
            print("Couldn't mkdir", AGENDA_ITEM_STORE,
                  ": not saving agenda items", file=sys.stderr)
            print(e, file=sys.stderr)
            AGENDA_ITEM_STORE = None

    if item_list and AGENDA_ITEM_STORE:
        try:
            # To create the filename, remove spaces, anything following a dash
            # then add the year and month
            bodyname = mtg["Name"].replace(' ', '').split('-')[0]
            itemfilebase = os.path.join(AGENDA_ITEM_STORE,
                                    bodyname + '-'
                                    + meetingtime.strftime('%Y-%m'))
            itemfile = itemfilebase + '.jsonl'
            with open(itemfile, 'a') as itemsfp:
                for item in item_list:
                    # item['body'] = bodyname
                    item['mtgdate'] = mtg['Meeting Date']
                    item['mtgname'] = mtg["Name"]
                    json.dump(item, itemsfp)
                    # json.dump doesn't add a newline
                    print('', file=itemsfp)
        except Exception as e:
            print("Exception trying to save item store from", mtg)
            print(e)

    # linkify links, particularly the Zoom link
    for link in soup.body.findAll(string=LINK_PAT):
        if type(link) is not NavigableString:
            continue
        url = str(link)
        print("linkifying", url, file=sys.stderr)
        atag = soup.new_tag("a", href=url)
        atag.string = url
        link.replace_with(atag)

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


def get_tickler(agenda_str, mtg, meetingtime, tickler_html_file):
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
    tickler_html = html_agenda_pdftohtml(mtg, meetingtime,
                                         url=tickler_url).decode()
    soup = BeautifulSoup(tickler_html, "lxml")

    # First give it a clear title. After html_agenda_pdf2html,
    # there's an h3 at the beginning with the date of the tickler.
    firstheader = soup.find('h3')
    if firstheader:
        headerchild = next(firstheader.children)
        headertext = headerchild.strip()
        if TICKLER_HDR_DATE_PAT.match(headertext):
            firstheader.name = 'h1'
            headerchild.replace_with("Tickler, " + headertext)
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

def write_files(mtglist):
    """Take a list of meeting dictionaries and make RSS and HTML files.
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
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">

<channel>
   <title>Los Alamos County Government Meetings</title>
   <link>{RSS_URL}losalamosmeetings</link>
   <description>An Unofficial, Non-Sanctioned Listing of Los Alamos Government Meetings, provided by Akkana Peck.</description>
   <language>en</language>
   <copyright>Public Domain</copyright>
   <ttl>14</ttl>
   <pubDate>{gendate}</pubDate>
   <managingEditor>akk at shallowsky dot com (Akkana Peck)</managingEditor>
   <atom:link href="{RSS_URL}" rel="self" type="application/rss+xml" />
   <generator>losalamosmtgs</generator>
""",
              file=rssfp)

        print(html_head("Los Alamos County Government Meetings"), file=htmlfp)
        print(f"""As of: {gendate}
 ... <a href="about.html">About Los Alamos Meetings (How to Use This Page)</a>
 ... <a href="{RSS_URL}index.rss">Los Alamos Meetings RSS2.0 Feed</a>.

""", file=htmlfp)

        agendafile = None
        agenda_html = None
        meetingtime = None

        no_agenda_yet = []

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
                tickler_filepath = get_tickler(agenda_html, mtg, meetingtime,
                                               tickler_filename)
                desc = f"County Council Tickler for {meetingtimestr}"
                # lastmod = datetime.datetime.now()
                # guid = tickler_filename
                # url = f"{RSS_URL}{tickler_filename}"

                # Add to the RSS
                if tickler_filepath:
                    active_meetings.append(tickler_filename)
                    print(rss_entry(title=desc,
                                    desc=desc,
                                    guid=tickler_filename,
                                    url=f"{RSS_URL}{tickler_filename}",
                                    lastmod=now),
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
            cleanname = mtg['cleanname']

            if not mtg["Agenda"]:      # No agenda posted yet
                no_agenda_yet.append(mtg)
                print(cleanname, "has no agenda to fetch")
                agenda_html = None
                continue

            print(cleanname, "has an agenda: fetching it")
            # XXX TEMPORARY: save the PDF filename, because sometimes
            # pdftohtml produces an HTML file with no content even
            # though there's content in the PDF.
            pdfout = os.path.join(RSS_DIR, cleanname + ".pdf")
            try:
                agenda_html = agenda_to_html(mtg,
                                             meetingtime,
                                             save_pdf_filename=pdfout)
            except ReadTimeoutError:
                print("Timed out on " + agendaloc)
                agenda_html = NO_AGENDA
                agendastatus = "timeout"

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
                        print("There was a previous agenda:")
                    if agenda_html == NO_AGENDA:
                        print(oldhtml)
                        print("  ... but now:")
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
                with open(agendafile, 'wb') as outfp:
                    outfp.write(agenda_html)

            # Either way, this meeting is still listed:
            # note it so it won't be cleaned from the directory.
            active_meetings.append(cleanname)

            # Get the old JSON for this meeting, if any
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
                    # print("Nothing has changed, keeping lastmod")
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
            # (re)write the JSON file.
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
<a href="{mtg['Agenda']}" target='_none'>Agenda PDF</a><br>
</p>
"""

            if mtg["Agenda Packets"]:
                # The agenda packet links tend to have & in them
                # and so need to be escaped with CDATA
                if 'http' in mtg["Agenda Packets"]:
                    desc += f"""<p><a href="{mtg["Agenda Packets"]}" target="_none">Agenda Packet</a></p>\n"""
                else:
                    desc = f"""<p>Agenda packet: {mtg["Agenda Packets"]}</p>\n"""
                # XXX TODO:
                # Fetch the PDF agenda packet;
                # there are two inner tabs, Details and Reports
                # under Details are links to the Attachments
                # under Reports may be other links, e.g. Staff Report
                # so try to fetch all of these links and show them
                # The packet is, fortunately, HTML
                # Packet:  https://losalamos.legistar.com/LegislationDetail.aspx?ID=6448866&GUID=37428716-C1EB-412C-9BA4-5DDE1ADCACF2&Options=&Search=
                # Details: https://losalamos.legistar.com/LegislationDetail.aspx?ID=6448866&GUID=37428716-C1EB-412C-9BA4-5DDE1ADCACF2&Options=&Search=#
                # Details: https://losalamos.legistar.com/LegislationDetail.aspx?ID=6448866&GUID=37428716-C1EB-412C-9BA4-5DDE1ADCACF2&Options=&Search=#
                # But the links don't work without JS!
                # There may be no way to get to them.
                # Try using the dev tools network inspector to see what
                # URL is actually followed clicking on each of those links.
                # Details has cookie: Setting-69-Calendar Options=info|; Setting-69-Calendar Year=2023; Setting-69-Calendar Body=All; Setting-69-ASP.calendar_aspx.gridCalendar.SortExpression=MeetingStartDate DESC; Setting-69-ASP.meetingdetail_aspx.gridMain.SortExpression=Sequence ASC; Setting-69-ASP.legislationdetail_aspx.tabTop.TabIndex=1; ASP.NET_SessionId=up0olsdiy2cigdbhr1oi52jc; BIGipServerinsite.legistar.com_443=908198666.47873.0000
                # Set-Cookie: Setting-69-ASP.legislationdetail_aspx.tabTop.TabIndex=0; expires=Sun, 12-Dec-2123 05:00:00 GMT; path=/; secure
                # Reports has cookie: Setting-69-Calendar Options=info|; Setting-69-Calendar Year=2023; Setting-69-Calendar Body=All; Setting-69-ASP.calendar_aspx.gridCalendar.SortExpression=MeetingStartDate DESC; Setting-69-ASP.meetingdetail_aspx.gridMain.SortExpression=Sequence ASC; Setting-69-ASP.legislationdetail_aspx.tabTop.TabIndex=0; ASP.NET_SessionId=up0olsdiy2cigdbhr1oi52jc; BIGipServerinsite.legistar.com_443=908198666.47873.0000
                # Set-Cookie: Setting-69-ASP.legislationdetail_aspx.tabTop.TabIndex=1; expires=Sun, 12-Dec-2123 05:00:00 GMT; path=/; secure

                # The Set-Cookie legislationdetail_aspx.tabTop.TabIndex changes!

            print("GUID will be", mtg['GUID'], "lastmod is", mtg['lastmod'])

            # Add the item to the RSS
            print(rss_entry(title=f'{mtgtitle} {agenda_hdr}',
                            desc=f'{mtgtitle} {agenda_hdr}',
                            guid=mtg['GUID'], url=link,
                            lastmod=mtg['lastmod']), file=rssfp)

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

        # Done looping over meetings. Check for any new records.
        record_str, recordfile = write_meeting_records_file()
        if record_str and recordfile:
            print("<h2>Meeting Records (Minutes, Audio, Video)</h2>", file=htmlfp)
            print(f"<p>\n{ record_str }", file=htmlfp)
            print(f'<p><a href="{ recordfile }">See records available</a>',
                  file=htmlfp)
            url = RSS_URL + recordfile
            print(rss_entry(title="Meeting records",
                            desc=record_str,
                            guid=recordfile,
                            url=url,
                            lastmod=utcnow.strftime(RSS_DATE_FORMAT)),
                  file=rssfp)
        else:
            print("<p>\nNo new meeting records.", file=htmlfp)

        # Are there any meetings with no agenda yet?
        # XXX This should update the file only if new meetings have been posted.
        if not no_agenda_yet:
            try:
                os.unlink(no_agenda_path)
            except:
                pass
        else:
            no_agenda_file = "no-agenda.html"
            no_agenda_path = os.path.join(RSS_DIR, no_agenda_file)
            lastmod_noagenda = datetime.datetime.min
            with open(no_agenda_path, "w") as na_fp:
                print(html_head("Scheduled Meetings, No Agenda Yet"),
                      file=na_fp)
                lastmod_all = EARLY_DATETIME
                for mtg in no_agenda_yet:
                    mtgdate = datetime.datetime.strptime(mtg["Meeting Date"],
                                                         "%m/%d/%Y")
                    print("<p>\n%s %s: %s\n" % (mtgdate.strftime("%b %d, %Y"),
                                                mtg["Meeting Time"],
                                                mtg["Name"]),
                          file=na_fp)
                    try:
                        mtg_lastmod = datetime.datetime.strftime(
                            mtg['lastmod'], RSS_DATE_FORMAT)
                    except KeyError as e:
                        mtg_lastmod = now
                    except Exception as e:
                        mtg_lastmod = now
                        print("Exception with lastmod", e)
                        print("on", mtg)
                    if mtg_lastmod > lastmod_all:
                        lastmod_noagenda = mtg_lastmod

            # Now the no_agenda file is written. Add it to the RSS and HTML.
            lastmod_str = lastmod_noagenda.strftime(RSS_DATE_FORMAT)
            print(rss_entry(title="Meetings with no agenda",
                            desc="Scheduled meetings with no agenda yet",
                            guid="%s-%s" % (no_agenda_file,
                                time.mktime(lastmod_noagenda.timetuple())),
                            url=no_agenda_file,
                            lastmod=lastmod_str),
                  file=rssfp)
            print("""<h2>Recently scheduled meetings</h2>
<p>
<a href='%s'>Meetings that have been scheduled</a>
but have no agenda yet""" % no_agenda_file, file=htmlfp)

        print("</channel>\n</rss>", file=rssfp)
        print("</body>\n</html>", file=htmlfp)

    print("Wrote", outrssfilename, "and", outhtmlfilename)

    # Remove obsolete files for meetings no longer listed.
    for f in os.listdir(RSS_DIR):
        # Only clean up certain extensions:
        rmexts = [ '.json', '.rss', '.html', '.pdf' ]
        name, ext = os.path.splitext(f)
        if ext not in rmexts:
            continue

        # Protected files: don't remove these
        if f.startswith("index") or f.startswith("about"):
            continue
        if f.startswith('records'):
            continue
        if f.startswith('no-agenda'):
            continue
        # *-meeting-records.html will be managed by write_meeting_records_file()
        # and only deleted when a new one is to be added.
        if f.endswith(RECORDS_FILEBASE):
            continue

        def is_active(f):
            for act in active_meetings:
                if f.startswith(act):
                    return True
            return False

        if not is_active(f):
            print("removing", f)
            os.unlink(os.path.join(RSS_DIR, f))

def write_meeting_records_file():
    """Write one file holding all the meeting records we've seen,
       but only if there's something newer than the last known records.
       Return a string summarizing today's new records,
       which can be used in both HTML and RSS indices,
       plus the filename of the most recent records file.
    """
    initialized = False
    filename = None
    recordfp = None
    newrecords = []
    most_recent_date = EARLY_DATE

    # Find any existing meeting records files.
    # There should be no more than one, but allow for mistakes.
    old_records = []
    for f in os.listdir(RSS_DIR):
        if f.endswith(RECORDS_FILEBASE):
            old_records.append(f)

    if len(old_records) > 1:
        old_records.sort()

    def delete_old_records():
        for r in old_records:
            os.unlink(os.path.join(RSS_DIR, r))

    records = mtg_records.records_by_date()
    if not records:
        return "No meeting records", None

    # First pass to determine the most recently added record
    for rec in records:
        recdate = datetime.datetime.strptime(rec["latest-record"],
                                             "%Y-%m-%d").date()
        rec["Updated"] = recdate
        if recdate > most_recent_date:
            most_recent_date = recdate

    if most_recent_date == EARLY_DATE:
        # There are no meeting records
        return "", None

    # Get the date the most recent records file was last written
    old_record_file = None
    try:
        old_record_file = old_records[-1]
        old_records_date = os.stat(
            os.path.join(RSS_DIR, old_record_file)).st_mtime
        # This is a float. Turn it into a datetime.date
        old_records_date = datetime.date.fromtimestamp(old_records_date)
    except FileNotFoundError:
        old_records_date = EARLY_DATE
    except IndexError:
        old_records_date = EARLY_DATE

    if old_records_date == EARLY_DATE:
        old_records_datestr = "[a while ago]"
    else:
        old_records_datestr = old_records_date.strftime("%Y-%m-%d")

    if most_recent_date <= old_records_date:
        return f"""There shouldn't be anything new here;
The most recent record is {old_records_datestr}""", old_record_file

    # Okay, there are new records to display. Rewrite the records file.
    # Second pass through records.
    # Have to re-initialize the generator
    records = mtg_records.records_by_date()
    recordfp = None
    for rec in records:
        # Retrieve the datetime.date that was set in the first pass
        recdate = rec["Updated"]
        if (today - recdate).days < 5:
            if not initialized:
                filename = f'{ todaystr }-{RECORDS_FILEBASE}'
                recordfp = open(os.path.join(RSS_DIR, filename), 'w')
                print(
                    html_head(title=f"Recent Meeting Records as of {todaystr}"),
                    file=recordfp)
                print("""<p>
Dates are when the record was last updated.
<p>
To see any of these records, go to the
<a href="https://losalamos.legistar.com/Calendar.aspx" target="_blank">Legistar
calendar page</a>, then set the Month appropriately (e.g. <i>Last Month</i>).
Don't forget to set the Month back to Current Month when you're done.
Sorry, Legistar doesn't allow links directly to meeting records.
<p>
Also, if you need to download the audio, clicking on <i>Audio download</i>
from Legistar doesn't seem to work; instead, click on <i>Video</i>
instead, and from the Video page, click on <i>Download</i>,
then <i>Audio Download.</i>""",
                      file=recordfp)

                # print a header if there are any new records at all for this meeting
                print("<table border=1>\n <tr>\n  <th>Name", file=recordfp)
                for rkey in MeetingRecords.RECORD_TYPES:
                    print("  <th>%s" % rkey, file=recordfp)

                initialized = True

            newrecords.append(f"{rec['name']} (updated {rec['Updated']})")

        retstr = ""
        print(" <tr>\n  <td><b>%s</b>" % rec['name'], file=recordfp)

        for rkey in MeetingRecords.RECORD_TYPES:
            if rkey not in rec or not rec[rkey]:
                print("   <td>&nbsp;", file=recordfp)
                continue
            # "Updated" is a datetime, which json can't serialize.
            # Skip it; "latest-record" is the serialized/stringified version.
            if rkey == "Updated":
                continue

            # Don't add links: the Legistar links are bogus and don't work
            # print(rec['name'], ": adding record for", rkey)
            print("<td>%s" % rec[rkey][1], file=recordfp)
            if False and rec[rkey][0]:
                s = f'<a href="{ rec[rkey][0] }" target="_none">{ rkey }</a>'
            else:
                s = rkey
            s += f' ({rec[rkey][1]})'
            retstr += s + '\n'

        print("</tr>", file=recordfp)

    if recordfp:
        print("</body></html>", file=recordfp)
        recordfp.close()

        if Verbose:
            print("Wrote meeting records file", filename)

        # In that case, remove any older records files.
        for oldrec in old_records:
            if oldrec == filename:
                print("EEK! Would have removed the records file just written",
                      filename)
                continue
            if Verbose:
                print("Removing old record file file", oldrec)
            os.unlink(os.path.join(RSS_DIR, oldrec))

        retstr = "<p>\nRecent records for:\n<ul>\n<li>" \
            + '\n<li>'.join(newrecords) \
            + "\n</ul>"

        return retstr, filename

    # If we get here, recordfp didn't get set,
    # which means there weren't any recent records
    # (but somehow it didn't get picked up earlier)
    if Verbose:
        print("Confused, thought there were recent records but there aren't")
    return "", None


VALID_FILENAME_CHARS = "-_." + string.ascii_letters + string.digits

def clean_filename(badstr):
    return ''.join(c for c in badstr if c in VALID_FILENAME_CHARS)


def mtgdic_to_cleanname(mtgdic):
    """A standard way to turn date and committee name into something
       that can be used for filenames or URLs.
       Will be used both for the agenda file and for RSS entries.
    """
    mtg_dt = meeting_datetime(mtgdic)
    if not mtg_dt:
        print("eeg, no mtg_dt for", mtgdic)
        return "notime-" + clean_filename(mtgdic["Name"])

    # If it has a nonzero hour, include that as part of the cleanname.
    # Some bodies, like the County Council and BPU, schedule closed and
    # open sessions consecutively on the same evening.
    if hasattr(mtg_dt, 'hour') and mtg_dt.hour:
        return mtg_dt.strftime("%Y-%m-%d_%H") + '-' \
            + clean_filename(mtgdic["Name"])

    return mtg_dt.strftime("%Y-%m-%d") + '-' \
        + clean_filename(mtgdic["Name"])


if __name__ == '__main__':
    if len(sys.argv) > 1:
        RSS_DIR = sys.argv[1]

        RSS_URL = sys.argv[2]
        # RSS_URL is a directory and must end with a slash
        if not RSS_URL.endswith('/'):
            RSS_URL += '/'

    build_upcoming_meetings_list()

    write_files(upcoming_meetings)

