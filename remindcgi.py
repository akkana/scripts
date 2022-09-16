#!/usr/bin/env python3

"""CGI script to run /usr/bin/remind and output as HTML"""

import cgi
import subprocess
import re
import os, sys
from datetime import date, datetime, timedelta, MAXYEAR


today = date.today()

css = '''@media (prefers-color-scheme: dark) {
  * { background: black; color: white; }
  a:link { color: #ffff00; }
  a:visited { color: #aaffaa; }
  a:hover, a:active { color: #ffffaa; }
}
@media (prefers-color-scheme: light) {
  * { background: #eff;}
}
'''


# termcolor.colored wasn't working, and termcolor.cprint doesn't help
# when trying to combine several formatting items.
# colorama is primarily aimed at Windows, and doesn't have styles
# Windows lacks, like italic (termcolor doesn't have italic either).
# So instead, see https://stackoverflow.com/a/51708889
class ColorFormat:
    # Foreground
    F_Default = "\x1b[39m"
    F_Black = "\x1b[30m"
    F_Red = "\x1b[31m"
    F_Green = "\x1b[32m"
    F_Yellow = "\x1b[33m"
    F_Blue = "\x1b[34m"
    F_Magenta = "\x1b[35m"
    F_Cyan = "\x1b[36m"
    F_LightGray = "\x1b[37m"
    F_DarkGray = "\x1b[90m"
    F_LightRed = "\x1b[91m"
    F_LightGreen = "\x1b[92m"
    F_LightYellow = "\x1b[93m"
    F_LightBlue = "\x1b[94m"
    F_LightMagenta = "\x1b[95m"
    F_LightCyan = "\x1b[96m"
    F_White = "\x1b[97m"

    # Formatting
    Bold = "\x1b[1m"
    Dim = "\x1b[2m"
    Italic = "\x1b[3m"
    Underlined = "\x1b[4m"
    Blink = "\x1b[5m"
    Reverse = "\x1b[7m"
    Hidden = "\x1b[8m"

    # Reset part
    Reset_Bold = "\x1b[21m"
    Reset_Dim = "\x1b[22m"
    Reset_Italic = "\x1b[23m"
    Reset_Underlined = "\x1b[24"
    Reset_Blink = "\x1b[25m"
    Reset_Reverse = "\x1b[27m"
    Reset_Hidden = "\x1b[28m"


class TextFormatter:
    REMINDDIR = os.path.expanduser("~/web/cal/")

    @staticmethod
    def linkify(word):
        if is_link(word):
            return "%s%s%s%s%s" % (ColorFormat.F_Blue, ColorFormat.Italic,
                                   word,
                                   ColorFormat.Reset_Italic,
                                   ColorFormat.F_Default)
        return word

    @staticmethod
    def highlight(line):
        return "%s%s%s" % (ColorFormat.Bold,
                           line,
                           ColorFormat.Reset_Bold)
        return line

    @staticmethod
    def header(line):
        return "%s%s%s%s%s%s\n" % (ColorFormat.F_Magenta, ColorFormat.Bold,
                                  "**** ", line,
                                  ColorFormat.Reset_Bold,
                                  ColorFormat.F_Default)
        return line

    @staticmethod
    def linebreak():
        return ""

    @staticmethod
    def eventbreak():
        return ""

    @staticmethod
    def separator():
        return "--------------"

    @staticmethod
    def print_head(title):
        print(TextFormatter.header(title))

    @staticmethod
    def print_foot():
        pass


class HTMLFormatter:
    REMINDDIR = os.getcwd()

    @staticmethod
    def linkify(line):
        line = line.strip()
        if is_link(line):
            return '<a href="%s">%s</a>' % (line, line)
        return line

    @staticmethod
    def header(line):
        return f"<h2>{line}</h2>"

    @staticmethod
    def highlight(line):
        return f"<strong>{line}</strong>"

    @staticmethod
    def linebreak():
        return "<br />"

    @staticmethod
    def eventbreak():
        return "<p>"

    @staticmethod
    def separator():
        return "<hr>"

    @staticmethod
    def print_head(title):

        # There doesn't seem to be any way to get the current URL in a
        # Python CGI. os.environ["REQUEST_URI"] is the closest, but it doesn't
        # have the schema or server name.
        # So build it up from the components in the environment:
        # print("SERVER_NAME:", os.environ["SERVER_NAME"], file=sys.stderr)
        # print("REQUEST_URI:", os.environ["REQUEST_URI"], file=sys.stderr)

        fullurl = f'{os.environ["REQUEST_SCHEME"]}://' \
            f'{os.environ["SERVER_NAME"]}' \
            f'{os.environ["REQUEST_URI"]}'

        # Strip off the query string. urlparse or urlsplit from urllib.parse
        # seem like they ought to be the way to do that, except that they
        # give path='//cal/' so you have to do string manipulation anyway
        # to fix that. Seems like urllib.parse is more trouble than it's worth.
        baseurl = fullurl.split('?')[0]
        # print("baseurl:", baseurl, file=sys.stderr)

        print(f'''Content-type: text/html

<html>
<head>
 <title>{title}</title>

 <meta http-equiv="content-type" content="text/html; charset=utf-8" />

 <!-- Google insists on this for "mobile friendly" sites: -->
 <meta name="viewport" content="width=device-width, initial-scale=1">

 <style>
{css}
 </style>

</head>

<body>
<h1>{title}</h1>
<p>
<a href="{baseurl}?when=remind">Reminders</a> &bull;
<a href="{baseurl}?when=week">Week</a> &bull;
<a href="{baseurl}?when=month">Month</a> &bull;
<a href="{baseurl}?when=all">All Events</a>
<p>
''')

    @staticmethod
    def print_foot():
        print(f'''
</body>
</html>
''')


def is_link(word):
    """Ultra-simple and dumb link detector.
       Could improve, but in this context links are likely to be simple.
    """
    return word.startswith('http')


def linkify_line(line, formatter):
    return ' '.join([formatter.linkify(w) if is_link(w) else w
                     for w in line.split()])


def print_remind_for_interval(enddate, formatter):
    """Print everything output by remind -n between now and the end date.
       That means everything except that for repeating events, only the
       first instance will be printed.
    """
    remindout = subprocess.check_output(["/usr/bin/remind", "-n",
                                         os.path.join(formatter.REMINDDIR,
                                                      "remind.txt")])
    lines = remindout.decode().split('\n')
    # lines look like
    # 2022/08/27 on Saturday, August 27th: some meeting||zoomlink||more info
    # so a simple alphanumeric sort will work to sort by date
    lines.sort()

    monthname = None
    weeknum = None   # Actually a string of the week number
    for line in lines:
        if not line:
            continue
        try:
            d = datetime.strptime(line[:10], '%Y/%m/%d').date()
        except ValueError:
            print("Couldn't parse", line[:10],
                  ": full line was '", line, formatter.eventbreak())
            continue
        if d > enddate:
            break

        newmonth = d.strftime("%b")
        if newmonth != monthname:
            monthname = newmonth
            print(formatter.header(monthname))
        newweeknum = d.strftime("%U")
        if newweeknum != weeknum:
            weeknum = newweeknum
            print(formatter.separator())

        sublines = line.replace('||', '\n').split('\n')
        firstline = sublines[0][11:]

        # If remind has added an "on longday, longmonth Nth, remove it
        # and add the date back at the beginning in an easier to read format.
        firstline = '%s: %s' % (
            d.strftime('%a, %-d %b'),
            re.sub('on [A-Z][a-z]+day, [A-Z][a-z]+ [0-9]{1,2}[a-z]{2}',
                   '', firstline))

        print(formatter.highlight(firstline))
        for subline in sublines[1:]:
            print(formatter.linebreak(), linkify_line(subline, formatter))
        print(formatter.eventbreak())

    formatter.print_foot()


def print_reminders(formatter):
    """Print an only slightly spruced-up version of
       remind -g output, which only reminds about things today
       and things that have a +N reminder window set up.
    """
    remindout = subprocess.check_output(["/usr/bin/remind", "-g",
                                         os.path.join(formatter.REMINDDIR,
                                                      "remind.txt")])
    remindout = remindout.decode().replace("||", "\n")

    new_event = True
    for line in remindout.split('\n'):
        line = line.strip()
        if not line:
            new_event = True
            continue
        line = formatter.linkify(line)
        if new_event:
            print(formatter.eventbreak(), formatter.highlight(line))
        else:
            print(line, formatter.linebreak())
        new_event = False

    formatter.print_foot()


if __name__ == '__main__':
    if 'REQUEST_METHOD' in os.environ:
        formatter = HTMLFormatter()

        form = cgi.FieldStorage()

        if 'when' in form:
            when = form['when'].value.lower()
        else:
            when = None
    else:
        if len(sys.argv) <= 1:
            when = None
        else:
            when = sys.argv[1].lower()

        formatter = TextFormatter()

    if not when:
        when = "week"
    if when == "all":
        # Show everything
        formatter.print_head("All Events")
        enddate = date(MAXYEAR, 12, 31)
    elif when == "week":
        formatter.print_head("Upcoming Week")
        enddate = today + timedelta(days=7)
    elif when == "month":
        formatter.print_head("Upcoming Month")
        enddate = today + timedelta(days=31)
    elif when == "remind":
        formatter.print_head("Reminders")
    else:
        # Show everything
        print(f"<p>\nDon't understand when '{when}';",
              "showing all events", file=sys.stderr)
        print("Usage: %s [week|month|remind]"
              % os.path.basename(sys.argv[0]))
        sys.exit(0)

    print("Today is", today.strftime("%A, %B %-d"))
    print(formatter.linebreak())

    if when == "remind":
        print_reminders(formatter)
    else:
        print_remind_for_interval(enddate, formatter)

