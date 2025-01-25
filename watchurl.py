#!/usr/bin/env python3

# Watch a given URL and send an email if it's been modified in the last
# day/week/month.
# Python requests doesn't seem to do If-Modified-Since,
# so this fetches the headers and compares dates.
# If an email address is provided as a third argument,
# will email when there are changes: meant to be used as a cron script.


import requests
from datetime import datetime
from dateutil.parser import parse as parsedate
from dateutil.relativedelta import relativedelta
from email.mime.text import MIMEText
import socket    # for getting hostname
import smtplib
import sys


def check_if_changed(url, howlong, email):
    """howlong is 'day', 'week', 'month'
    """
    now = datetime.now().astimezone()
    if howlong == 'month':
        when = now - relativedelta(months=3)
    elif howlong == 'week':
        when = now -relativedelta(days=7)
    else:
        if howlong != 'day':
            print(f"Don't understand '{howlong}': assuming 1 day",
                  file=sys.stderr)
        when = now - relativedelta(days=1)

    r = requests.head(url)
    try:
        url_datetime = parsedate(r.headers['last-modified'])
    except KeyError:
        print(url, "doesn't have a last-modified header", file=sys.stderr)
        return

    # print("url_datetime:", url_datetime)
    # print("when:", when)
    # file_time = datetime.datetime.fromtimestamp(os.path.getmtime(dstFile))

    if url_datetime <= when:
        print(url, "hasn't changed in a", howlong)
        return

    # It has changed. Send email?
    message = f"{url} changed {now - url_datetime} ago"
    print(message)
    if email:
        send_mail(email, "A URL you're watching has changed", message)


def send_mail(recipient, subject, body):
    print("Sending mail to", recipient)
    msg = MIMEText(body)
    msg['Subject'] = subject
    sender = "Watchurl <noreply@%s>" % socket.getfqdn()
    msg['From'] = sender
    msg['To'] = recipient
    msg['User-Agent'] = 'Python Email+SMTPlib'

    s = smtplib.SMTP('localhost')
    s.sendmail(sender, [recipient], msg.as_string())
    s.quit()


if __name__ == '__main__':
    url = sys.argv[1]
    howlong = sys.argv[2]
    if len(sys.argv) > 3:
        email = sys.argv[3]
    else:
        email = None
    check_if_changed(url, howlong, email)

