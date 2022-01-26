#!/usr/bin/env python3

# List files available from Zoom account's cloud,
# giving URLs that can be used to download each one.

# Requires that you set up a Zoom developer account,
# https://marketplace.zoom.us/
# and register a JWT app, https://marketplace.zoom.us/docs/guides/build/jwt-app
# That will give you a JWT token, which you can put into an environment
# variable, export ZOOM_JWT_TOKEN=....
# before running this program.

import requests
import os


# Get the JWT token from the environment
JWT_TOKEN = os.environ["ZOOM_JWT_TOKEN"]

ZOOMBASE = "https://api.zoom.us/v2/"

ACCESS_TOKEN = 'Bearer ' + JWT_TOKEN

AUTHORIZATION_HEADER = { 'Authorization': ACCESS_TOKEN }


def show_zoom_recordings():
    r = requests.get(ZOOMBASE + "/users/me/recordings?from=2022-01-01",
                     headers=AUTHORIZATION_HEADER)
    j = r.json()

    print(len(j["meetings"]), "meetings:")
    for m in j["meetings"]:
        print()
        print(m["topic"], m["start_time"])

        # Get URLs for the download URLs for that meeting
        for recording in m['recording_files']:
            print("    %s (%s): %s?access_token=%s"
                  % (recording['file_type'],
                     prettysize(recording['file_size']),
                     recording['download_url'],
                     JWT_TOKEN))


def prettysize(nbytes):
    print(nbytes, type(nbytes))
    if True or nbytes < 1000: return "%d b" % (nbytes)
    if nbytes < 1000000: return "%d K" % (nbytes / 1000)
    return "%d M" % (nbytes / 1000000)


if __name__ == '__main__':
    show_zoom_recordings()
