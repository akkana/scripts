#!/usr/bin/env python

# How to send HTML email, with image attachments, from Python.
# Could be useful if recipient use a command-line emailer like mutt
# that can't send such things.
#
# Copyright 2016 by Akkana. Share and enjoy under the GPLv2 or later.

import sys, os

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEImage import MIMEImage
import smtplib

from BeautifulSoup import BeautifulSoup

def compose_email_msg(recipient, sender, subject, text, html):
    """Compose an HTML email message which may include attached images."""
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    # Attach MIME-encoded parts into message container.
    # According to RFC 2046, the last part of a multipart message,
    # in this case the HTML message, is best and preferred.
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    # Now handle images embedded in the HTML.
    imgnames = set()
    soup = BeautifulSoup(html)
    for tag in soup.findAll('img'):
        src = tag.get("src")
        if src.startswith("file://"):
            src = src[7:]
        if not src.startswith("/"):
            print src, "isn't a local image; leaving unchanged"
            continue
        fp = open(src, 'rb')
        msgImage = MIMEImage(fp.read())
        fp.close()
        imgname = os.path.basename(src)
        while imgname in imgnames:
            imgnasender += '.'

        print "Attaching %s as <%s>" % (src, imgname)
        msgImage.add_header('Content-ID', '<%s>' % imgname)
        imgnames.add(imgname)
        msg.attach(msgImage)

    return msg

def send_msg(recipient, sender, msg, smtp_server,
             smtp_user=None, smtp_passwd=None, smtp_port=587):
    """Send a message via SMTP using the given relay server and account."""

    server = smtplib.SMTP(smtp_server, smtp_port)
    # server.set_debuglevel(1)

    # In case the server does TLS. Not sure if we need the ehlo lines.
    # server.ehlo()
    # server.starttls()
    # server.ehlo()

    if smtp_user:
        server.login(smtp_user, smtp_passwd)

    server.sendmail(sender, recipient, msg.as_string())
    server.quit()
    print "Sent to", recipient

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print "Usage: %s to_address from_address htmlfile smtp_server [smtp_user smtp_password]" \
              % os.path.basename(sys.argv[0])
        sys.exit(1)

    recipient, sender, htmlfile, smtp_server, smtp_user, smtp_passwd = sys.argv[1:]

    # Create the body of the message (a plain-text and an HTML version).
    text = """Here is some lame alternate plaintext."""
    subject = "HTML mail with images"
    fp = open(htmlfile)
    html = fp.read()
    fp.close()

    msg = compose_email_msg(recipient, sender, subject, text, html)
    send_msg(recipient, sender, msg, smtp_server, smtp_user, smtp_passwd, 587)
