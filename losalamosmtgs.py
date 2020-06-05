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
# from pprint import pprint


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
now = datetime.datetime.utcnow()


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
                dic[fieldnames[i]] = field.text.strip()

        if "Meeting Date" in dic and "Meeting Time" in dic:
            mtg_datetime = meeting_datetime(dic)
            if only_past and mtg_datetime < utcnow:
                # print(dic["Name"], "meeting on", mtg_datetime,
                #       "already happened")
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


def get_html_agenda_pdfminer(agendaloc):
    """Convert a PDF agenda to text and/or HTML using pdfminer.
       pdfminer doesn't give very clean output, so this is optional and
       the imports are only loaded the first time this function is called.
       Probably better: pdftohtml -c -s -i -noframes abc.pdf abc.html
       Returns bytes, not str. I think.
    """
    try:
        fh = open(agendaloc, 'rb')
    except FileNotFoundError:
        response = requests.get(agendaloc, stream=True)
        # response.raw supposedly gives a file handle,
        # but it's not seekable and pdfminer needs to seek.
        # fh = response.raw
        fh = io.BytesIO(response.content)

    try:
        resource_manager = PDFResourceManager()
    except UnboundLocalError:
        from pdfminer.layout import LAParams, LTTextBox
        from pdfminer.pdfpage import PDFPage
        from pdfminer.pdfinterp import PDFResourceManager
        from pdfminer.pdfinterp import PDFPageInterpreter
        from pdfminer.converter import TextConverter, HTMLConverter

        resource_manager = PDFResourceManager()

    # The fake file object needs to be StringIO for TextConverter,
    # BytesIO for HTMLConverter.
    # fake_file_handle = io.StringIO()
    fake_file_handle = io.BytesIO()
    converter = HTMLConverter(resource_manager, fake_file_handle,
                              laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
        page_interpreter.process_page(page)

    text = fake_file_handle.getvalue()

    # close open handles
    fh.close()
    converter.close()
    fake_file_handle.close()

    return text


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
            print(mtg['cleanname'], "Agenda changed")

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

                elif not lastmod:
                    lastmod = datetime.datetime.strptime(oldmtg['lastmod'],
                                                         RSS_DATE_FORMAT)
            except RuntimeError:
                print("Error reading jsonfile")
                changestr += "Error reading jsonfile<p>"
                lastmod = now

        else:
            lastmod = now

        # The meeting has already been saved to JSON,
        # so it's safe to add other keys to it now.
        # Save the change string to put it in the RSS later.
        mtg['changestr'] = changestr

        # Either way, this meeting is still listed:
        # note it so it won't be cleaned from the directory.
        active_meetings.append(mtg['cleanname'])

        # If the meeting is new or something has changed,
        # (re)write the JSON file.
        with open(jsonfile, 'w') as jsonfp:
            mtg['lastmod'] = lastmod.strftime(RSS_DATE_FORMAT)
            jsonfp.write(json.dumps(mtg))

    # Finally, generate the RSS file.
    outfilename = os.path.join(RSS_DIR, "index.rss")
    with open(outfilename, 'w') as outfp:
        gendate = now.strftime(RSS_DATE_FORMAT)
        print(f"""<?xml version="1.0" encoding="iso-8859-1" ?>
<rss version="2.0"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

<channel>
   <title>Los Alamos County Government Meetings</title>
   <link>{RSS_URL}losalamosmeetings</link>
   <description>An Unofficial, Non-Sanctioned Listing of Los Alamos Government Meetings, provided by Akkana Peck</description>
   <language>en</language>
   <copyright>Public Domain</copyright>
   <ttl>14</ttl>
   <pubDate>{gendate}</pubDate>
   <managingEditor>akk at shallowsky dot com (Akkana Peck)</managingEditor>
   <generator>losalamosmtgs</generator>
""",
              file=outfp)

        for mtg in mtglist:
            desc = f"""The {mtg['Name']} will meet on {mtg['Meeting Date']} at {mtg['Meeting Time']}.
"""
            link = f"{RSS_URL}{mtg['cleanname']}.html"
            if mtg["Agenda"]:
                desc = f"""{desc}<p><b>**** There is an agenda. ****</b></p>\n"""
            else:
                desc += "<p>No agenda is available.</p>\n"
            if mtg['changestr']:
                desc += "<p>" + mtg['changestr'] + '\n'

            print("packet", mtg["Agenda Packets"])
            if mtg["Agenda Packets"]:
                if 'http' in mtg["Agenda Packets"]:
                    desc += f"""<p>There is an <a href="{mtg["Agenda Packets"]}">Agenda Packet</a></p>\n"""
                else:
                    desc = f"""<p>Agenda packet: {mtg["Agenda Packets"]}</p>\n"""

            if mtg['Meeting Location']:
                desc += "<p>" + mtg['Meeting Location'] + "</p>"

            print(f"""<item>
   <title>{mtg['Name']} on {mtg["Meeting Date"]}</title>
   <guid isPermaLink="false">{mtg['cleanname']}.{lastmod.strftime("%Y%m%d-%H%M")}</guid>
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

