#!/usr/bin/env python3

# Scrape the Los Alamos meetings page to be alerted to what's on
# the agenda at upcoming meetings.
# Make it available via RSS.

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
import pytz


# Where to start: the public legistar meeting list
MEETING_LIST_URL = "http://losalamos.legistar.com/Calendar.aspx"

# The place where the RSS will be hosted. Must end with a slash.
# The RSS file will be this/index.rss.
RSS_URL = "http://localhost/los-alamos-meetings/"

# Where to put the generated RSS file. Customize this for your website.
RSS_DIR = os.path.expanduser("~/web/los-alamos-meetings")
if not os.path.exists(RSS_DIR):
    os.makedirs(RSS_DIR)

mountain_time = pytz.timezone('America/Denver')

# Try to make now an aware datetime.
# You might think that utcnow() would already be timezone aware,
# given that it's explicitly UTC, but that would be giving
# way more credit to the datetime designers than is due.
# You can't do it with .astimezone(pytz.utc) either, because
# it converts back to localtime and then converts to utc.
now = datetime.datetime.utcnow()
now = now.replace(tzinfo=pytz.utc)

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
            else:
                # Some fields, like Location, have simple formatting in them
                # such as <br>. But they're also full of formatting
                # we don't want, like font specifiers and colors,
                # so ' '.join([str(c) for c in field.contents])
                # is too much. Might be worth writing a
                # simplified_html_snippet() some day.
                # But for now, notice that BS .text puts in \r\n for <br>,
                # so substitute a <br> back:
                dic[fieldnames[i]] = field.text.strip().replace('\r\n',
                                                                '<br>')

        if "Meeting Date" in dic and "Meeting Time" in dic:
            mtg_datetime = meeting_datetime(dic)
            if only_past and mtg_datetime < utcnow:
                continue

        upcoming.append(dic)

    return upcoming


def meeting_datetime(mtg):
    """Parse the meeting date and time and return an aware UTC time.
    """
    # The parsed time is in GMT no matter what and is unaware,
    # because strptime can't create a timezone aware object.
    unaware = datetime.datetime.strptime(mtg["Meeting Date"] + " "
                                         + mtg["Meeting Time"],
                                         '%m/%d/%Y %I:%M %p')
    localtime = mountain_time.localize(unaware)
    return localtime.astimezone(pytz.utc)


def get_html_agenda_pdftohtml(agendaloc):
    """Convert a PDF agenda to text and/or HTML using pdftohtml,
       removing the idiotic dark grey background pdftohtml has hardcoded in.
       Returns bytes, not str.
    """
    r = requests.get(agendaloc, timeout=30)
    pdffile = os.path.join(tempdir, "agenda.pdf")
    htmlfile = os.path.join(tempdir, "agenda.html")
    with open(pdffile, "wb") as pdf_fp:
        pdf_fp.write(r.content)
    subprocess.call(["pdftohtml", "-c", "-s", "-i", "-noframes",
                     pdffile, htmlfile])
    with open(htmlfile, 'rb') as htmlfp:
        html = htmlfp.read()

    # Replace the grey background that htmltotext wires in
    soup = BeautifulSoup(html, "lxml")
    body = soup.body
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

    return soup.prettify(encoding='utf-8')


VALID_FILENAME_CHARS = "-_." + string.ascii_letters + string.digits

def clean_filename(badstr):
    return ''.join(c for c in badstr if c in VALID_FILENAME_CHARS)


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
            agenda_html = get_html_agenda_pdftohtml(mtg["Agenda"])

        # RSS doesn't deal well with feeds where some items have
        # a <link> and others don't. So make an empty file to keep
        # RSS readers happy.
        else:
            agenda_html = b"<html><body><p>No agenda available.</body></html>"

        agendafile = os.path.join(RSS_DIR, mtg['cleanname'] + ".html")

        # See if there was already an agenda there:
        if os.path.exists(agendafile):
            with open(agendafile, "rb") as oldfp:
                oldhtml = oldfp.read()
        else:
            oldhtml = ""

        if agenda_html != oldhtml:
            with open(agendafile, 'wb') as outfp:
                outfp.write(agenda_html)
            # Mark it as changed
            lastmod = now
            changestr += "<p>The agenda has changed.</p>"
            print(mtg['cleanname'], "Agenda changed", "lastmod is", lastmod)
        else:
            print("The agenda hasn't changed")

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

            desc = f"""<![CDATA[ The {mtg['Name']} will meet on {mtg['Meeting Date']} at {mtg['Meeting Time']}.
"""
            link = f"{RSS_URL}{mtg['cleanname']}.html"
            if mtg["Agenda"]:
                desc = f"""{desc}<p> <a href="{mtg["Agenda"]}"<b>**** There is an agenda PDF. ****</b></a><br>(Click on the rss item link to see it as HTML).</p>\n"""
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

            if mtg['Meeting Location']:
                desc += "<p>" + mtg['Meeting Location'] + "</p>"

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
            os.unlink(f)


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

