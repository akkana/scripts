#!/usr/bin/env python

# How to send HTML email, with image attachments, from Python.
# Could be useful if you use a command-line emailer like mutt
# that can't send such things.
#
# Copyright 2016 by Akkana. Share and enjoy under the GPLv2 or later.

import sys, os

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEImage import MIMEImage
import smtplib

def compose_email_msg(you, me, subject, text, html, imgfile):
    """Compose an HTML email message with a single attached image."""
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = me
    msg['To'] = you

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    fp = open(imgfile, 'rb')
    msgImage = MIMEImage(fp.read())
    fp.close()
    msgImage.add_header('Content-ID', '<image1>')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)
    msg.attach(msgImage)

    return msg

def send_msg(you, me, msg, smtp_server,
             smtp_user=None, smtp_passwd=None, smtp_port=587):
    """Send a message via SMTP using the given relay server and account."""

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.set_debuglevel(1)

    # Not sure if we need the ehlo lines to start TLS:
    # server.ehlo()
    # server.starttls()
    # server.ehlo()

    if smtp_user:
        server.login(smtp_user, smtp_passwd)

    server.sendmail(me, you, msg.as_string())
    server.quit()

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print "Usage: %s to_address from_address imgfile smtp_server [smtp_user smtp_password]" \
              % os.path.basename(sys.argv[0])
        sys.exit(1)

    you, me, imgfile, smtp_server, smtp_user, smtp_passwd = sys.argv[1:]

    # Create the body of the message (a plain-text and an HTML version).
    text = """Hi!
How are you?
Here is the link you wanted:
  https://docs.python.org/2/library/email-examples.html
"""

    html = """\
<html>
<head></head>
<body>
<p>Hi!<br>
   How are you?<br>
   Here is <a href="https://docs.python.org/2/library/email-examples.html">the link you wanted</a>.
</p>
<p><img align=right src="cid:image1">
  And here is an image, and it should be aligned
  all to the right of this text.
</p><p>
  Blah, blah, blah, blah, blah, blah, blah, blah, blah,
  blah, blah, blah, blah, blah, blah, blah, blah, blah,
  blah, blah, blah, blah, blah, blah, blah, blah, blah,
  blah, blah, blah, blah, blah, blah, blah, blah, blah,
  blah, blah, blah, blah, blah, blah, blah, blah, blah,
  blah!
</p>
</body>
</html>
"""
    subject = "Here, have a text message"

    msg = compose_email_msg(you, me, subject, text, html, imgfile)
    send_msg(you, me, msg, smtp_server, smtp_user, smtp_passwd, 587)
