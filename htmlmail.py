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

from bs4 import BeautifulSoup

def compose_email_msg(recipient, sender, html, text=None):
    """Compose an HTML email message which may include attached images.
       @param recipient Email address of the recipient
       @param sender Email address of the sender
       @param html The HTML desired for the body.
                   The first <title> or <h1> tag will be used as the subject.
       @param text Optional text part:
                   If False or None, no text part will be sent.
                   If True, we'll try to generate plaintext from the HTML.
                   Otherwise pass in the desired plain text (str or unicode).
       @return A MIME message object.
    """
    soup = BeautifulSoup(html, "lxml")

    # Attach MIME-encoded parts into message container.
    # According to RFC 2046, the last part of a multipart message,
    # in this case the HTML message, is best and preferred.

    # Special case: text=True will ask BeautifulSoup to convert
    # the HTML into text. Otherwise, pass in a text part if you want it.
    # If text is None, no text part will be attached.
    if (text == True):
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(soup.get_text(), 'plain'))
    elif (text):
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(text, 'plain'))
    else:
        # No text part, so we don't need multipart/alternative.
        # However, we may still want to attach images, so we still
        # need multipart/related.
        msg = MIMEMultipart('related')

    # XXX Note that we might want multipart/mixed if we ever add
    # other types of file attachments besides images embedded in HTML.
    # Basically, we eventually want structure like:
    # mixed
    #     alternative
    #         text
    #         related
    #             html
    #             inline image
    #             inline image
    #     attachment
    #     attachment

    # Now the container is created, so we can add sender and recipient.
    msg['From'] = sender
    msg['To'] = recipient

    # See if the HTML message already has a subject,
    # either in <title> or <h1>. If not, use a default.
    title = soup.find("title")
    if title:
        subject = title.string.strip()
    else:
        title = soup.find("h1")
        if title:
            subject = title.text.strip()
        else:
            subject = "An HTML message"

    print "Subject is", subject
    msg['Subject'] = subject

    # Attach the HTML part.
    msg.attach(MIMEText(html, 'html'))

    # Now handle any images embedded in the HTML.
    # XXX We might want to get the findAll img list first,
    # because if there are no images, we can use MIME non-multipart.
    imgnames = set()
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

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print "Usage: %s to_address from_address htmlfile smtp_server [smtp_user smtp_password]" \
              % os.path.basename(sys.argv[0])
        sys.exit(1)

    recipient, sender, htmlfile, smtp_server, smtp_user, smtp_passwd = sys.argv[1:]

    with open(htmlfile) as fp:
        html = fp.read()
    msg = compose_email_msg(recipient, sender, html)
    send_msg(recipient, sender, msg, smtp_server, smtp_user, smtp_passwd, 587)
