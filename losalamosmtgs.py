#!/usr/bin/env python3

# Scrape the Los Alamos meetings page to be alerted to what's on
# the agenda at upcoming meetings.

import requests
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urljoin


def parse_meeting_list():
    """Parse the HTML page listing meetings,
       returning a list of dictionaries for each upcoming meeting
       (but not past ones).
    """
    now = datetime.datetime.now()
    now = datetime.datetime(2020, 5, 26, 18, 53, 14, 116219)

    meeting_list_url = "http://losalamos.legistar.com/Calendar.aspx"
    # meeting_list_url_parsed = urlparse(meeting_list_url)

    # r = requests.get(meeting_list_url, timeout=30)
    # soup = BeautifulSoup(r.text, 'lxml')
    soup = BeautifulSoup(open("Calendar.aspx").read(), "lxml")

    caltbl = soup.find("table",
                       id="ctl00_ContentPlaceHolder1_gridCalendar_ctl00")

    # The legend is in the thead
    fieldnames = []
    for i, field in enumerate(caltbl.thead.findAll("th")):
        if field.text:
            fieldnames.append(field.text.strip())
        else:
            fieldnames.append(str(i))

    # print("Field names:", fieldnames)

    upcoming = []

    for row in caltbl.tbody.findAll("tr"):
        dic = {}
        for i, field in enumerate(row.findAll("td")):
            if fieldnames[i].startswith("Agenda"):
                # If there's an Agenda URL, make it absolute.
                a = field.find("a")
                href = a.get("href")
                if href:
                    dic[fieldnames[i]] = urljoin(meeting_list_url, href)
                else:
                    dic[fieldnames[i]] = None
            else:
                dic[fieldnames[i]] = field.text.strip()

        if "Meeting Date" in dic and "Meeting Time" in dic:
            dic["datetime"] = datetime.datetime.strptime(dic["Meeting Date"]
                                                         + " "
                                                         + dic["Meeting Time"],
                                                         '%m/%d/%Y %I:%M %p')
            if dic["datetime"] < now:
                print(dic["Name"], "meeting on", dic["datetime"],
                      "already happened")
                continue

        upcoming.append(dic)

    return upcoming


from pdfminer.layout import LAParams, LTTextBox
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import TextConverter
import io


def parse_agenda(agendaloc):
    """Parse a PDF agenda using pdfminer.
       https://stackoverflow.com/a/56530666
    """
    try:
        fh = open(agendaloc, 'rb')
        print("Opened file", agendaloc)
    except FileNotFoundError:
        response = requests.get(agendaloc, stream=True)
        # response.raw supposedly gives a file handle,
        # but it's not seekable and pdfminer needs to seek.
        # fh = response.raw
        fh = io.BytesIO(response.content)
        print("Using requests for", agendaloc)

    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle,
                              laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
        page_interpreter.process_page(page)

    text = fake_file_handle.getvalue()

    # close open handles
    fh.close()
    converter.close()
    fake_file_handle.close()

    print(text)


if __name__ == '__main__':
    upcoming = parse_meeting_list()

    print("\nUpcoming meetings:")
    for mtg in upcoming:
        print(mtg["Name"], "---", mtg["Meeting Date"])
        print("    Agenda:", mtg["Agenda"])
        print("    Agenda Packets:", mtg["Agenda Packets"])
        if mtg["Agenda"]:
            # mtg["Agenda"] = "Agenda.pdf"
            print("\n\n***********")
            parse_agenda(mtg["Agenda"])
    else:
        print("No upcoming meetings")


