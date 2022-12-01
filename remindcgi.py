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

# Patterns used for restricting datetimes before parsing
datetimepat = re.compile('[\d:apm ]+')
datetimerangepat = re.compile('[\d:apm -]+')


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
        return "%s%s%s%s%s" % (ColorFormat.F_Blue, ColorFormat.Italic,
                               word,
                               ColorFormat.Reset_Italic,
                               ColorFormat.F_Default)

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
        return '<a href="%s">%s</a>' % (line, line)

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


#
# Regular expression to detect links. Start with just a simple one:
#
link_re = re.compile(r'((https?|ftp|file)://[\S]+)', flags=re.IGNORECASE)

def linkify_line(line, formatter):
    links = re.findall(link_re, line)
    # print("\n======== line:", line)
    # print("links:", links)
    if not links:
        # print("  No links in line")
        return line
    linkified_string = ''
    for link in links:
        # print("link:", link)

        # If there are any capture groups in the RE, findall returns
        # a tuple containing each of the matched groups.
        # But specifying multiple schemas, like allowing for file://,
        # unfortunately gets treated as a capture group. So there has
        # to be another capture group around the whole expression,
        # and that group will show up as the first item in the tuple.
        link = link[0]
        pos = line.find(link)
        # print("  pos:", pos)
        # Add text leading up to the link
        linkified_string += line[:pos]
        # print("  Adding non-link text", line[:pos])
        # Add the linkified link
        # print("  Adding linkified", link)
        linkified_string += formatter.linkify(link)
        # print("  linkified_string now:", linkified_string)
        # Move to after the link
        line = line[pos + len(link):]
        # print("  Rest of string is now:", line)

    linkified_string += line
    return linkified_string


# The remind program has % codes to show when events are happening.
# That means that strings like URLs that contain % will be interpreted
# as remind codes. So remove those remind codes, since this program
# prints its own dates, and then escape any remaining %.
# Pattern to match % followed by a single alphanumeric char:
PERCENTPAT = re.compile(
    rb"(^|\s)"    # beginning of string or whitespace
    rb"%[a-z\d]"  # remind time directive, e.g. %k
    rb"($|:|\s)"  # end of string, colon, or whitespace
)
# Remove the percent-escape, but keep the whitespace around it.
PERCENTREPL = rb"\1\2"

def print_remind_for_interval(enddate, formatter):
    """Print everything output by remind -n between now and the end date.
       That means everything except that for repeating events, only the
       first instance will be printed.
    """
    with open(os.path.join(formatter.REMINDDIR, "remind.txt"), 'rb') as infp:
        remindin = infp.read()

    # Replace any %x directives that are by themselves as words
    remindin = re.sub(PERCENTPAT, PERCENTREPL, remindin)
    # Escape any remaining % characters. For instance, in webex links.
    remindin = remindin.replace(b'%', b'%%')

    proc = subprocess.Popen(["/usr/bin/remind", "-n", "-" ],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    remindout = proc.communicate(input=remindin)[0]
    lines = remindout.decode().split('\n')
    # lines look like
    # 2022/08/27 on Saturday, August 27th: some meeting||zoomlink||more info
    # so a simple alphanumeric sort almost works to sort by date,
    # but AM/PM issues throw it off, so use datetimekey.
    lines.sort(key=datetimekey)

    monthname = None
    weeknum = None   # Actually a string of the week number
    for line in lines:
        line = line.strip()
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

        newmonth = d.strftime("%B")
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
            re.sub('on [A-Z][a-z]+day, [A-Z][a-z]+ [0-9]{1,2}[a-z]{2} *',
                   '', firstline))

        firstline = linkify_line(firstline, formatter)
        print(formatter.highlight(firstline))
        for subline in sublines[1:]:
            print(formatter.linebreak(), linkify_line(subline, formatter))
        print(formatter.eventbreak())

    formatter.print_foot()


def datetimekey(s):
    """ Take a date string of form yyyy/mm/dd maybetime more stuff
        where maybetime can have lots of forms.
        dateutil.parser.parse() is good at parsing different formats,
        but it can't handle extra stuff in the line, or ranges.
    """
    savedate = s[:10]
    m = re.match(datetimerangepat, s[11:])
    if not m:
        return s
    timerange = m.group(0).strip().replace(' ', '')
    if timerange.endswith(':'):
        timerange = timerange[:-1]

    # Now timerange might be something like '5:30-7pm'
    timeparts = timerange.split('-')

    # We only care about the first timepart, but need to know
    # if it ends with an 'am' or 'pm' (1-4pm) unless the first
    # part already has one (11am-1pm)
    lowertime = timeparts[0].lower()

    if lowertime.endswith('am'):
        # Make sure it's zero-prefixed
        hours = re.match('\d+', lowertime).group(0)
        houri = int(hours)
        return f'{savedate} {houri:02}'

    # The initial time (lowertime) could end with pm;
    # or the pm could be after the range end, 1-3pm
    if lowertime.endswith('pm') or timerange.lower().endswith('pm'):
        hours = re.match('\d+', lowertime).group(0)
        houri = int(hours)
        # Special rule for 12 pm
        if houri == 12:
            houri = 0
        # This only includes the hour:
        hours = f'{savedate} {houri+12:02}'
        # Add back in the minutes, if any
        colon = lowertime.find(':')
        if colon > 0:
            hours += lowertime[colon:]
        return hours

    # No am or pm specified
    return s


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

