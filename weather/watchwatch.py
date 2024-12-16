#!/usr/bin/env python3

# Monitor a watchweather instance, and send email if any of the
# clients seem to have hung, which unfortuantely happens regularly
# with the client for Ambient Weather's API.

import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import socket    # for getting hostname
import getpass   # for getting username
from datetime import datetime, timedelta
import sys


try:
    watchurl = sys.argv[1]
    recipient = sys.argv[2]
except:
    import os
    print("Usage: %s watchweather_url email_address"
          % os.path.basename(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


r = requests.get(watchurl)
soup = BeautifulSoup(r.text, 'lxml')

now = datetime.now()
curyear = str(now.year) + ' '

email_text = ''

for clientbox in soup.find_all('fieldset', class_='stationbox'):
    # datatable = list(clientbox.find_all('tr'))
    bottomrow = clientbox.find('td', colspan=True)

    # Watchweather doesn't include the year in its abbreviated page,
    # for space reasons. To keep datetime from being confused, add it.
    datetext = curyear + bottomrow.text.splitlines()[0]
    dt = datetime.strptime(datetext, '%Y %a %b %d %H:%M')

    if (now - dt).seconds > 2*3600:
        email_text += "%s hasn't reported since %s\n" % (clientbox.legend.text,
                                                         dt)

if email_text:
    email_text += "You may need to run systemctl restart watchweather\n"

    # print("Emailing to", recipient)
    # print("---")
    # print(email_text)
    # print("---")

    msg = MIMEText(email_text)
    msg['Subject'] = 'Watchweather failure'
    sender = "Watchweather Watcher <noreply@%s>" % socket.getfqdn()
    msg['From'] = sender
    msg['To'] = recipient
    msg['User-Agent'] = 'AkkMailer'

    s = smtplib.SMTP('localhost')
    s.sendmail(sender, [recipient], msg.as_string())
    s.quit()
