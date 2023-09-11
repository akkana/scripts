#!/usr/bin/env python3

# List Zoom cloud recordings available from the current year,
# giving URLs that can be used to download each one.

# Requires that you set up a Zoom developer account,
# https://marketplace.zoom.us/
# and register a server-to-server OAuth2 app,
#    https://developers.zoom.us/docs/internal-apps/create/
# That will give you a ACCOUNT_ID, CLIENT_ID and CLIENT_SECRET,
# which you can put into environment variables before running this program.


import requests
import subprocess
from datetime import date
from dateutil.relativedelta import relativedelta
import base64
import os, sys
# from pprint import pprint


# Get the Zoom account credentials from the environment
try:
    ACCOUNT_ID = os.environ["ZOOM_ACCOUNT_ID"]
    CLIENT_ID = os.environ["ZOOM_CLIENT_ID"]
    CLIENT_SECRET = os.environ["ZOOM_CLIENT_SECRET"]
except KeyError:
    print("Please export ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID and ZOOM_CLIENT_SECRET first")
    sys.exit(1)


def get_access_token():
    """Use the account id, client id and client secret to get an access token
    """

    url = "https://zoom.us/oauth/token?grant_type=account_credentials" \
        "&account_id=%s" % (ACCOUNT_ID)

    clientpair = f"{CLIENT_ID}:{CLIENT_SECRET}"
    base64_bytes = base64.b64encode(clientpair.encode("ascii"))

    payload = ""
    headers = {
        'Host': 'zoom.us',
        'Authorization': 'Basic %s' % (base64_bytes.decode())
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_j = response.json()
    # print("auth request returned:")
    # pprint(response_j)
    return response_j["access_token"]


def show_zoom_recordings(fromdate=None, fetch=False):
    """Show ll recordings from a given month.
       Zoom can only fetch one month at a time;
       pass in a datetime.date from which the month and year will be used.
       If no date is passed in, the current month will be used.
    """
    access_token = get_access_token()
    auth_header = {
        'Authorization': f'Bearer {access_token}',
        'Content-type': 'application/json',
    }

    # As of the switch to  OAuth, Zoom can only fetch one month at a time
    # (it used to handle wider ranges) except maybe for Pro accounts.
    today = date.today()
    if fromdate:
        todate = min(today, fromdate + relativedelta(months=1))
    else:
        todate = today
        fromdate = todate - relativedelta(months=1)

    recurl = "https://api.zoom.us/v2/users/me/recordings" \
        f'?from={fromdate.strftime("%Y-%m-%d")}' \
        f'&to={todate.strftime("%Y-%m-%d")}'
    # Zoom documents this variant which seemingly isn't date limited,
    # but apparently it only works for Pro accounts.
    # recurl = "https://api.zoom.us/v2/users/me/recordings"

    r = requests.get(recurl, headers=auth_header)
    j = r.json()

    try:
        nmeetings = len(j["meetings"])
    except KeyError as e:
        print(e)
        nmeetings = 0

    if not nmeetings:
        # print("No meetings! JSON was:")
        # pprint(j)
        return

    for m in j["meetings"]:
        print()
        print(m["topic"], m["start_time"])

        # e.g., "2022-01-20T18:44:47Z/LWVLA Lunch with a Leader"
        subdir = os.path.join(m["start_time"], m["topic"])
        os.makedirs(subdir, mode=0o755, exist_ok=True)

        # Get URLs for the download URLs for that meeting
        for recording in m['recording_files']:
            print("    %s (%s): %s"
                  % (recording['file_type'],
                     prettysize(recording['file_size']),
                     recording['download_url']))

            if not fetch:
                continue

            ext = recording["file_extension"].lower()
            filepath = os.path.join(subdir, "zoom."+ext)

            if not os.path.exists(filepath):
                print("    %s (%s): %s"
                      % (recording['file_type'],
                         prettysize(recording['file_size']),
                         recording['download_url']))
                url = recording["download_url"]
                if ext in ['txt', 'vtt']:
                    print("Trying to fetch", url)
                    r1 = requests.get(url,
                                      headers=auth_header)
                    with open(filepath, "wb") as outfile:
                        outfile.write(r1.content)
                    os.chmod(filepath, 0o444)
                else:
                    print("Calling yt-dlp")
                    subprocess.call(["yt-dlp", "-o", filepath, url],
                                    shell=False)


def prettysize(nbytes):
    if nbytes < 1000: return "%d b" % (nbytes)
    if nbytes < 1000000: return "%d K" % (nbytes / 1000)
    return "%d M" % (nbytes / 1000000)


if __name__ == '__main__':
    # First (and only) argument is a base directory into which to download
    if len(sys.argv) == 2:
        os.chdir(sys.argv[1])
        fetch = True
        print("Will try to download to", sys.argv[1])
    else:
        fetch = False
        print("Not downloading; specify download directory to download")

    # Set initial start date to the beginning of this year.
    today = date.today()
    start_date = date(today.year, 1, 1)
    while start_date < today:
        show_zoom_recordings(start_date, fetch=False)
        start_date += relativedelta(months=1)
