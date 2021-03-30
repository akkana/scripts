#!/usr/bin/env python3

# Scrape the Los Alamos meetings page to be alerted to what's on
# the agenda at upcoming meetings.
# Make it available via RSS.

# Suggestion: run this script via crontab:
# Use crontab -e to add a line like:
# 45  15  *  *  * python3 /path/tp/htdocs/losalamosmtgs.py > /path/to/htdocs/los-alamos-meetings/LOG 2>&1

import requests
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urljoin
import io
import string
import subprocess
import tempfile
import json
import os, sys
from lxml.html.diff import htmldiff


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
        parse_meeting_list(r.text, only_future)

    # Get the meetings on the default (this month) page.
    # These will be appended to the global list upcoming_meetings.
    r = requests.get(MEETING_LIST_URL, timeout=30)
    parse_meeting_list(r.text, only_future)

    # The meeting list is in date/time order, latest first.
    # Better to list them in the other order, starting with
    # meetings today, then meetings tomorrow, etc.
    # That's why we couldn't just write meetings from the earlier loop.
    # Could sort by keys, 'Meeting Date' and 'Meeting Time',
    # but since it's already sorted, it's easier just to reverse.
    upcoming_meetings.reverse()


def parse_meeting_list(page_html, only_future=False):
    """Parse the HTML page listing meetings,
       returning a list of dictionaries for each upcoming meeting
       (but not past ones).
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
    for i, field in enumerate(caltbl.thead.findAll("th")):
        if field.text:
            fieldnames.append(field.text.strip())
        else:
            fieldnames.append(str(i))

    # Loop over meetings, rows in the table:
    for row in caltbl.tbody.findAll("tr"):
        dic = {}
        # Loop over columns describing this meeting:
        for i, field in enumerate(row.findAll("td")):
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

        if "Meeting Date" in dic and "Meeting Time" in dic:
            mtg_datetime = meeting_datetime(dic)
            if only_future and mtg_datetime < utcnow:
                continue

        upcoming_meetings.append(dic)


def meeting_datetime(mtg):
    """Parse the meeting date and time and return an aware localtime.
    """
    # The parsed time is in the local time and is unaware,
    # because strptime can't create a timezone aware object (see above).
    unaware = datetime.datetime.strptime(mtg["Meeting Date"] + " "
                                         + mtg["Meeting Time"],
                                         '%m/%d/%Y %I:%M %p')
    # Make it aware in localtime
    localtime = unaware.astimezone(localtz)
    return localtime


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
<style>
ins { background: #9ff; }
del { background: #fbb; }
</style>
</head>

<body>
<h1>%s</h1>
''' % (title, title)

    diff += htmldiff(before_html, after_html)

    diff += "\n</body></html>\n"

    # encode to return bytes.
    return diff.encode()


def get_html_agenda_pdftohtml(agendaloc, save_pdf_filename):
    """Convert a PDF agenda to text and/or HTML using pdftohtml,
       removing the idiotic dark grey background pdftohtml has hardcoded in.
       save_pdf_name is for debugging: if set, save the PDF there
       and don't delete it.
       Returns bytes, not str.
    """
    r = requests.get(agendaloc, timeout=30)

    with open(save_pdf_filename, "wb") as pdf_fp:
        pdf_fp.write(r.content)
    htmlfile = save_pdf_filename + ".html"
    print("Calling", ' '.join(["pdftohtml", "-c", "-s", "-i", "-noframes",
                               "-enc", "utf-8",
                               save_pdf_filename, htmlfile]))
    subprocess.call(["pdftohtml", "-c", "-s", "-i", "-noframes",
                     save_pdf_filename, htmlfile])
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

    body = soup.body

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
    else:
        print(bodylen, "characters in body text")
        if bodylen < 10:
            print(f"Body text is: '{body.text}'")

    del body["bgcolor"]
    del body["vlink"]
    del body["link"]

    # Remove all the fixed pixel width styles
    for tag in soup.findAll('style'):
        tag.extract()
    for tag in soup.findAll('div'):
        del tag["style"]
    for tag in soup.findAll('p'):
        del tag["style"]
        # Consider also deleting tag["class"]

    # Or maybe the above changes were what removed the body contents?
    if not body.text:
        print("**Yikes! Our changes to", save_pdf_file,
              "made the HTML empty. Saving original instead.")
        with open(os.path.join(RSS_DIR, save_pdf_filename + "_cleaned.html"),
                  "w") as savfp:
            print(soup.prettify(encoding='utf-8'), file=savfp)
        return html

    return soup.prettify(encoding='utf-8')


VALID_FILENAME_CHARS = "-_." + string.ascii_letters + string.digits

def clean_filename(badstr):
    return ''.join(c for c in badstr if c in VALID_FILENAME_CHARS)


NO_AGENDA = b"No agenda available."

def write_rss20_file(mtglist):
    """Take a list meeting dictionaries
       and make RSS and HTML files from it.
    """
    active_meetings = []

    ##############
    # Generate index HTML and RSS file headerss.
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
  <link rel="alternate" type="application/rss+xml"
        title="Los Alamos Meetings Feed"
        href="{RSS_URL}index.rss" />
</head>
<body>
<h1>Los Alamos County Government Meetings</h1>
As of: {gendate}
 .......... <a href="{RSS_URL}index.rss">Los Alamos Meetings RSS2.0 Feed</a>.

""", file=htmlfp)

        for mtg in mtglist:

            # Is the meeting in the future? Don't list past meetings.
            meetingtime = meeting_datetime(mtg)
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
                    agenda_html = get_html_agenda_pdftohtml(mtg["Agenda"],
                                                save_pdf_filename=pdfout)
                except urllib3.exceptions.ReadTimeoutError:
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
            print("agenda filename", agendafile)

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
                with open(agendafile, 'wb') as outfp:
                    outfp.write(agenda_html)

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

            mtgtitle = f"""{mtg['Name']} on {mtg["Meeting Date"]}"""

            desc = f"""{mtg['Name']}: {mtg['Meeting Date']} at {mtg['Meeting Time']}<br />
"""

            # Set up the change strings for the header and body
            if agendastatus == "new":
                agenda_hdr = " (NEW AGENDA)"
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
                agenda_hdr = " (NO AGENDA)"
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
                    desc += f"""<p><a href="{mtg["Agenda Packets"]}">Agenda Packet PDF</a></p>\n"""
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

        if f.startswith("index"):
            continue

        def is_active(f):
            for act in active_meetings:
                if f.startswith(act):
                    return True
            return False

        if not is_active(f):
            print("removing", f)
            os.unlink(os.path.join(RSS_DIR, f))


def mtgdic_to_cleanname(mtgdic):
    """A standard way to turn date and committee name into something
       that can be used for filenames or URLs.
       Will be used both for the agenda file and for RSS entries.
    """
    return meeting_datetime(mtgdic).strftime("%Y-%m-%d") + '-' \
        + clean_filename(mtgdic["Name"])


if __name__ == '__main__':
    if len(sys.argv) > 1:
        RSS_URL = sys.argv[1]
        # RSS_URL is a directory and must end with a slash
        if not RSS_URL.endswith('/'):
            RSS_URL += '/'

        if len(sys.argv) > 2:
            RSS_DIR = sys.argv[2]

    build_upcoming_meetings_list()

    write_rss20_file(upcoming_meetings)


