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
import os


########## CONFIGURATION ##############

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


def parse_meeting_list(only_past=False):
    """Parse the HTML page listing meetings,
       returning a list of dictionaries for each upcoming meeting
       (but not past ones).
    """
    r = requests.get(MEETING_LIST_URL, timeout=30)
    soup = BeautifulSoup(r.text, 'lxml')

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

    upcoming = []

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
            if only_past and mtg_datetime < utcnow:
                continue

        upcoming.append(dic)

    return upcoming


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


NO_AGENDA = b"<html><body><p>No agenda available.</body></html>"

def write_rss20_file(mtglist):
    """Take a list meeting dictionaries and make an RSS file from it.
    """

    print("\n==== Generating RSS for", len(mtglist), "meetings")
    active_meetings = ["index.rss"]

    for mtg in mtglist:
        lastmod = None
        changestr = ""
        mtg['cleanname'] = mtgdic_to_cleanname(mtg)
        print(mtg["cleanname"])

        if mtg["Agenda"]:
            print(mtg["cleanname"], "has an agenda: fetching it")
            # XXX TEMPORARY: save the PDF filename, because sometimes
            # pdftohtml produces an HTML file with no content even
            # though there's content in the PDF.
            pdfout = os.path.join(RSS_DIR, mtg['cleanname'] + ".pdf")
            agenda_html = get_html_agenda_pdftohtml(mtg["Agenda"],
                                                    save_pdf_filename=pdfout)

        # RSS doesn't deal well with feeds where some items have
        # a <link> and others don't. So make an empty file to keep
        # RSS readers happy.
        else:
            agenda_html = b""

        # Does the agenda file need to be (re)written?
        write_agenda_file = False

        # See if there was already an agenda file left from previous runs:
        agendafile = os.path.join(RSS_DIR, mtg['cleanname'] + ".html")
        if os.path.exists(agendafile):
            with open(agendafile, "rb") as oldfp:
                oldhtml = oldfp.read()

            if oldhtml == NO_AGENDA:    # no agenda previously
                if agenda_html:         # but there is now
                    write_agenda_file = True
                    changestr += "<p><b>There is now an agenda.</b>"

            else:                       # there was a previous agenda
                if not agenda_html:     # ... which is gone now
                    changestr += \
                        "<p><b>An earlier agenda has been removed!</b>" \
                        "<p><b>Agenda saved here is the previous agenda.</b>"
                    # don't write over the old agenda file

                elif agenda_html != oldhtml:  # changed agenda
                    write_agenda_file = True
                    changestr += "<p><b>The agenda has changed.</b>"

        if write_agenda_file:
            if agenda_html:
                lastmod = now
            else:
                agenda_html = NO_AGENDA

            print("Writing a new agenda file")
            with open(agendafile, 'wb') as outfp:
                outfp.write(agenda_html)

        jsonfile = os.path.join(RSS_DIR, mtg['cleanname'] + ".json")
        if os.path.exists(jsonfile):
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
                    changestr += "<p>Changed: " + ', '.join(changed_keys) \
                        + "</p>"
                    print("Keys changed:", changed_keys, "lastmod is", lastmod)

                elif not lastmod:
                    print("Nothing has changed, keeping lastmod")
                    lastmod = datetime.datetime.strptime(oldmtg['lastmod'],
                                                         RSS_DATE_FORMAT)
            except RuntimeError:
                print("Error reading jsonfile")
                changestr += "Error reading jsonfile<p>"
                lastmod = now

        else:
            print("It's a new meeting, no previous jsonfile")
            lastmod = now

        mtg['lastmod'] = lastmod.strftime(RSS_DATE_FORMAT)
        mtg['GUID'] = mtg['cleanname'] + '.' + lastmod.strftime("%Y%m%d-%H%M")

        # Either way, this meeting is still listed:
        # note it so it won't be cleaned from the directory.
        active_meetings.append(mtg['cleanname'])

        # If the meeting is new or something has changed,
        # (re)write the JSON file. Don't save the changestr.
        if "changestr" in mtg:
            del mtg["changestr"]
        with open(jsonfile, 'w') as jsonfp:
            jsonfp.write(json.dumps(mtg, indent=4))

        # The meeting has been saved to JSON,
        # so it's safe to add other keys to it now.
        # Save the change string to put it in the RSS later.
        mtg['changestr'] = changestr

    # Finally, generate the index RSS file.
    outfilename = os.path.join(RSS_DIR, "index.rss")
    with open(outfilename, 'w') as outfp:
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
              file=outfp)

        # The meeting list is in date/time order, latest first.
        # Better to list them in the other order, starting with
        # meetings today, then meetings tomorrow, etc.
        # Could sort by keys, 'Meeting Date' and 'Meeting Time',
        # but since it's already sorted, it's easier just to reverse.
        mtglist.reverse()

        for mtg in mtglist:
            # Is the meeting in the future? Don't list past meetings.
            meetingtime = meeting_datetime(mtg)
            if meetingtime < now:
                print("Skipping", mtg["Name"], mtg["Meeting Date"],
                      "because", meetingtime, "<", now)
                continue

            desc = f"""<![CDATA[ The {mtg['Name']}: {mtg['Meeting Date']} at {mtg['Meeting Time']}<br />
"""

            if mtg['Meeting Location']:
                desc += "<br>Location:" + mtg['Meeting Location']

            link = f"{RSS_URL}{mtg['cleanname']}.html"
            if mtg["Agenda"]:
                desc = f"""{desc}<p> <a href="{mtg["Agenda"]}"<b>**** There is an agenda PDF. ****</b></a><br>
(Click on the rss item link to see it as HTML).</p>
"""
            else:
                desc += "<p>No agenda is available.</p>\n"
            if mtg['changestr']:
                desc += "<p>" + mtg['changestr'] + '\n'

                # print("packet", mtg["Agenda Packets"])
            if mtg["Agenda Packets"]:
                # The agenda packet links tend to have & in them
                # and so need to be escaped with CDATA
                if 'http' in mtg["Agenda Packets"]:
                    desc += f"""<p>There is an <a href="{mtg["Agenda Packets"]}">Agenda Packet PDF</a></p>\n"""
                else:
                    desc = f"""<p>Agenda packet: {mtg["Agenda Packets"]}</p>\n"""

            # Close the cdata thingie
            desc += "]]>"

            print("GUID will be", mtg['GUID'], "lastmod is", mtg['lastmod'])
            print(f"""<item>
   <title>{mtg['Name']} on {mtg["Meeting Date"]}</title>
   <guid isPermaLink="false">{mtg['GUID']}</guid>
   <link>{link}</link>
   <description>{desc}
   </description>
   <pubDate>{mtg['lastmod']}</pubDate>
</item>""", file=outfp)

        print("</channel>\n</rss>", file=outfp)

    print("Wrote", outfilename)

    # Remove obsolete files for meetings no longer listed.
    for f in os.listdir(RSS_DIR):
        # Only clean up .json, .rss, .html:
        if not f.endswith('.json') and not f.endswith('.rss') \
           and not f.endswith('.html'):
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
    meetings = parse_meeting_list()

    write_rss20_file(meetings)


