#!/usr/bin/env python

# How to send HTML email, with image attachments, from Python.
# Could be useful if recipient use a command-line emailer like mutt
# that can't send such things.
#
# Copyright 2016,2018 by Akkana. Share and enjoy under the GPLv2 or later.

import sys, os

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEImage import MIMEImage
from email.header import Header
import smtplib

from bs4 import BeautifulSoup

import argparse

def compose_email_msg(recipients, sender, html, text=None,
                      subject=None, cc=None, imagedir=None):
    """Compose an HTML email message which may include attached images.
       @param recipient Email address of the recipient
       @param sender Email address of the sender
       @param html The HTML desired for the body.
                   The first <title> or <h1> tag will be used as the subject.
       @param text Optional text part:
                   If False or None, no text part will be sent.
                   If True, we'll try to generate plaintext from the HTML.
                   Otherwise pass in the desired plain text (str or unicode).
       @param subject Optional subject. If not specified, it will be taken
                   from the title in the HTML part, if any;
                   if none,it will be some sort of lame default.
       @return A MIME message object.
    """
    soup = BeautifulSoup(html, "lxml")

    # Attach MIME-encoded parts into message container.
    # According to RFC 2046, the last part of a multipart message,
    # in this case the HTML message, is best and preferred.
    # In the general case, the structure looks like:
    # mixed
    #     alternative
    #         text
    #         related
    #             html
    #             inline image
    #             inline image
    #     attachment
    #     attachment
    # For now we don't handle attachments other than embedded images
    # so we don't need mixed.

    # Are there any embedded images? We aren't ready to use them now,
    # but we need to know whether to use MIME multipart/related.
    embedded_images = soup.findAll('img')

    # If there are embedded images, rewrite their src tags before
    # attaching the html part.
    # imgnames is a dictionary of mime_name: pathname_on_disk
    imgnames = {}
    for tag in embedded_images:
        src = tag.get("src")
        if src.startswith("file://"):
            src = src[7:]
        if not src.startswith("/"):
            if imagedir:
                srcpath = os.path.join(imagedir, src)
                if os.path.exists(srcpath):
                    src = srcpath
                else:
                    print "Can't find", src, "in", imagedir, "leaving unchanged"
                    continue
            else:
                print src, "isn't a local image; leaving unchanged"
                continue

        # Now src points to the file path of the image.
        imgname = os.path.basename(src)
        while imgname in imgnames:
            imgname += '_'
        # Now it's unique
        imgnames[imgname] = src

        # imgname is what will be used when attaching the image.
        # So rewrite the HTML tag to use cid:imgname.
        tag['src'] = 'cid:' + imgname

    # Do we need to UTF-encode anything in the message?
    # This clause would make sense if input was unicode,
    # but it's actually bytes read in with fp.read().
    # if contains_non_ascii_characters(html):
    #     print "Encoded:", html.encode('utf-8')
    #     print "."
    #     html_mime = MIMEText(html.encode('utf-8'), 'html','utf-8')
    # else:
    #     html_mime = MIMEText(html, 'html')
    # So for now, let's assume the bytes read in are always UTF-8
    # and send them with that encoding:

    if embedded_images:
        # If we have embedded images, then the image tags have been changed
        # and we need to regenerate the HTML from the soup.
        html_part = MIMEMultipart('related')
        html_part.attach(MIMEText(str(soup), 'html','utf-8'))
    else:
        html_part = MIMEText(html, 'html','utf-8')

    # Attach the text and HTML parts.
    # Special case: text=True will ask BeautifulSoup to convert
    # the HTML into text. Otherwise, pass in a text part if you want it.
    # If text is None, no text part will be attached.
    if not text:
        msg = html_part
    elif text == True:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(soup.get_text(), 'plain'))
        msg.attach(html_part)
    else:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(html_part)

    # Now the container is created, so we can add sender and recipient.
    msg['From'] = encode_header(sender)
    msg['To'] = ', '.join([encode_header(r) for r in recipients])
    if cc:
        msg['Cc'] = ', '.join([encode_header(r) for r in cc])

    # If a subject wasn't specified,
    # see if the HTML message already has a subject,
    # either in <title> or <h1>. If not, use a default.
    if not subject:
        title = soup.find("title")
        if title:
            subject = title.string.strip()
        else:
            title = soup.find("h1")
            if title:
                subject = title.text.strip()
            else:
                subject = "An HTML message"

    # print "Subject is", subject
    msg['Subject'] = encode_header(subject)

    # Now handle any images embedded in the HTML.
    # XXX We might want to get the findAll img list first,
    # because if there are no images, we can use MIME non-multipart.
    for imgname in imgnames:
        src = imgnames[imgname]
        fp = open(src, 'rb')
        msgImage = MIMEImage(fp.read())
        fp.close()

        print "Attaching %s as <%s>" % (src, imgname)
        msgImage.add_header('Content-ID', '<%s>' % imgname)
        html_part.attach(msgImage)

    return msg

def contains_non_ascii_characters(s):
    return not all(ord(c) < 128 for c in s)

def encode_header(header_txt):
    if contains_non_ascii_characters(header_txt):
        return Header(header_txt, 'utf-8')
    else:
        return header_txt

def send_msg(recipients, sender, msg, smtp_server,
             smtp_user=None, smtp_passwd=None, smtp_port=587):
    """Send a message via SMTP using the given relay server and account."""

    print "Sending to recipients:", ', '.join(recipients)
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.set_debuglevel(1)

    # In case the server does TLS. Not sure if we need the ehlo lines.
    server.ehlo()
    server.starttls()
    server.ehlo()

    if smtp_user:
        server.login(smtp_user, smtp_passwd)

    server.sendmail(sender, recipients, msg.as_string())
    server.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=\
"""Send an HTML file as properly formatted mail, including any inline images.

Address lists may be comma separated""",
                             formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-c', '--cc', action="store", dest="cc",
                        help='cc addresses')
    parser.add_argument('-b', '--bcc', action="store", dest="bcc",
                        help='Bcc addresses')
    parser.add_argument('-s', '--subject', action="store", dest="subject",
                        help='The Subject of the mail (otherwise will use HTML title)')
    parser.add_argument('-t', '--text', action="store", dest="text_part",
                        help='Optional text part')

    parser.add_argument('-u', '--user', action="store", dest="smtp_user",
                        help='SMTP username')
    parser.add_argument('-p', '--password', action="store",
                        dest="smtp_password", help='SMTP password')

    parser.add_argument('to_addresses', help='The address the mail will be to')
    parser.add_argument('from_address',
                        help='The address the mail will be from')
    parser.add_argument('html_file', help='The HTML file to send')
    parser.add_argument('smtp_server', help='The SMTP server')

    args = parser.parse_args()

    with open(args.html_file) as fp:
        html = fp.read()

    recipients = args.to_addresses.split(',')

    if args.cc:
        cc = [ s.strip() for s in args.cc.split(',') ]
    else:
        cc = []
    if args.bcc:
        bcc = [ s.strip() for s in args.bcc.split(',') ]
    else:
        bcc = []

    msg = compose_email_msg(recipients, args.from_address, html, cc=args.cc,
                            subject=args.subject, text=args.text_part,
                            imagedir=os.path.dirname(
                                os.path.realpath(args.html_file)))

    send_msg(recipients + cc + bcc, args.from_address, msg,
             args.smtp_server, args.smtp_user, args.smtp_password, 587)
