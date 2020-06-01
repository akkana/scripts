#!/usr/bin/env python3

# Scrape the Los Alamos meetings page to be alerted to what's on
# the agenda at upcoming meetings.

import requests
from bs4 import BeautifulSoup
import datetime


def parse_meeting_list():
    now = datetime.datetime.now()

    # meeting_list_url = 'http://losalamos.legistar.com/Calendar.aspx'
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

    for row in caltbl.tbody.findAll("tr"):
        dic = {}
        for i, field in enumerate(row.findAll("td")):
            if fieldnames[i].startswith("Agenda"):
                a = field.find("a")
                dic[fieldnames[i]] = a.get("href")
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

        print(dic["Name"], "---", dic["Meeting Date"])
        print("  Agenda:", dic["Agenda"])
        print("  Agenda Packets:", dic["Agenda Packets"])


if __name__ == '__main__':
            parse_meeting_list()


