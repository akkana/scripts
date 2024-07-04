#!/usr/bin/env python3

# Monitor a URL and report when it changes.
# Write change times to a log file.
# Usage: whenupdated url logfile.
# Suggestion: put it in crontab every half-hour,
# 0,30 * * * * python whenupdated.py


from datetime import datetime
import requests
import sys, os


DATEFORMAT = '%Y-%m-%dT%H:%M'

def checkupdate(datadir, url):
    # Create the directory if not already there
    try:
        os.mkdir(datadir)
    except FileExistsError:
        pass

    # include a file with the URL, for human eyes
    urlfile = os.path.join(datadir, "URL")
    try:
        with open(urlfile) as urlfp:
            lasturl = urlfp.read().strip()
            if lasturl != url:
                raise RuntimeError("Eek, URL changed from '%s' to '%s'"
                                   % (url, lasturl))
    except FileNotFoundError:
        # First time through. Write the URL.
        with open(urlfile, 'w') as urlfp:
            print(url, file=urlfp)

    # Find the latest version in the datadir.
    # Version files have form version-%Y-%m-%d %H:%M
    files = os.listdir(datadir)
    files.sort(reverse=True)
    print("Reverse sorted files:", files)
    lastversion = ''
    for filename in files:
        if filename.startswith("version"):
            lastversion = filename
            print("lastversion:", lastversion)
            break

    lastbytes = b''
    if lastversion:
        try:
            with open(os.path.join(datadir, lastversion), 'rb') as fp:
                lastbytes = fp.read().strip()
        except FileNotFoundError:
            pass

    r = requests.get(url)
    newbytes = r.content.strip()
    if newbytes != lastbytes:
        print("They're different!")
        print("Old:", lastbytes)
        print("New:", newbytes)
        curversion = 'version-' + datetime.now().strftime(DATEFORMAT)
        with open(os.path.join(datadir, curversion), 'wb') as fp:
            fp.write(newbytes)
        print("Wrote", curversion)
    else:
        print("Hasn't changed")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: whenupdated datadir url")
        sys.exit(1)

    checkupdate(sys.argv[1], sys.argv[2])

