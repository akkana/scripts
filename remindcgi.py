#!/usr/bin/env python3

"""CGI script to run /usr/bin/remind and output as HTML"""

import cgi
import subprocess
import os, sys
from datetime import date, datetime, timedelta


# There doesn't seem to be any way to get the current URL in a
# Python CGI. os.environ["REQUEST_URI"] is the closest, but it doesn't
# have the schema or server name.
# So build it up from the components in the environment:
fullurl = f'{os.environ["REQUEST_SCHEME"]}://{os.environ["SERVER_NAME"]}' \
    f'/{os.environ["REQUEST_URI"]}'
# print("fullurl:", fullurl, file=sys.stderr)

# Strip off the query string. urlparse or urlsplit from urllib.parse
# seem like they ought to be the way to do that, except that they
# give path='//cal/' so you have to do string manipulation anyway
# to fix that. Seems like urllib.parse is more trouble than it's worth.
baseurl = fullurl.split('?')[0]
# print("baseurl:", baseurl, file=sys.stderr)


def linkify(line):
    line = line.strip()
    if line.startswith('http'):
        return '<a href="%s">%s</a>' % (line, line)
    return line


def print_head(title):
    print(f'''Content-type: text/html

<html>
<head>
 <title>{title}</title>

 <meta http-equiv="content-type" content="text/html; charset=utf-8" />

 <!-- Google insists on this for "mobile friendly" sites: -->
 <meta name="viewport" content="width=device-width, initial-scale=1">

</head>

<body>
<h1>{title}</h1>
<p>
<a href="{baseurl}">Reminders</a> &bull;
<a href="{baseurl}?interval=week">Week</a> &bull;
<a href="{baseurl}?interval=month">Month</a>
<p>
''')


form = cgi.FieldStorage()
if 'interval' in form:
    interval = form['interval'].value

    today = date.today()
    if interval.lower() == "week":
        print_head("This Week")
        enddate = today + timedelta(days=7)
    elif interval.lower() == "month":
        print_head("This Month")
        enddate = today + timedelta(days=31)
    else:
        import sys
        print(f"Unknown interval '{interval}'", file=sys.stderr)
        print_head("This Month")
        enddate = today + timedelta(days=31)

    remindout = subprocess.check_output(["/usr/bin/remind", "-n",
                                         os.path.join(os.getcwd(),
                                                      "remind.txt")])
    lines = remindout.decode().split('\n')
    # lines look like '2022/08/27 on Saturday, August 27th: dark-sky night'
    # so a simple alphanumeric sort will work
    lines.sort()

    for line in lines:
        if not line:
            continue
        try:
            d = datetime.strptime(line[:10], '%Y/%m/%d').date()
        except ValueError:
            print("Couldn't parse", line[:10],
                  ": full line was '", line, "'<p>")
            continue
        if d > enddate:
            break
        sublines = line.replace("||", "\n").split('\n')
        print(f"<b>{sublines[0]}</b><br>")
        for subline in sublines[1:]:
            print(linkify(subline), "<br>")
        print("<p>")

else:
    print_head("Reminders")
    remindout = subprocess.check_output(["/usr/bin/remind", "-g",
                                         os.path.join(os.getcwd(),
                                                      "remind.txt")])
    remindout = remindout.decode().replace("||", "\n")

    new_event = True
    for line in remindout.split('\n'):
        # ultra-simple linkify: assume the whole line is the link
        line = line.strip()
        if not line:
            new_event = True
            print('<p>')
            continue
        line = linkify(line)
        if new_event:
            print(f'<strong>{line}</strong>')
        else:
            print(line)
        print('<br>')
        new_event = False

print(f'''
</body>
</html>
''')

