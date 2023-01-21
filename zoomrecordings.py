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
import subprocess
import os, sys


# Get the JWT token from the environment
try:
    JWT_TOKEN = os.environ["ZOOM_JWT_TOKEN"]
except KeyError:
    print("Please export ZOOM_JWT_TOKEN='YOUR-ZOOM-JWT-TOKEN' first")
    sys.exit(1)

ZOOMBASE = "https://api.zoom.us/v2/"

ACCESS_TOKEN = 'Bearer ' + JWT_TOKEN

AUTHORIZATION_HEADER = { 'Authorization': ACCESS_TOKEN }


def show_zoom_recordings(fetch=False):
    r = requests.get(ZOOMBASE + "/users/me/recordings?from=2022-01-01",
                     headers=AUTHORIZATION_HEADER)
    j = r.json()

    try:
        print(len(j["meetings"]), "meetings:")
    except KeyError as e:
        print(e)
        print("No meetings! JSON was:")
        from pprint import pprint
        pprint(j)
        return

    for m in j["meetings"]:
        print()
        print(m["topic"], m["start_time"])

        # e.g., "2022-01-20T18:44:47Z/LWVLA Lunch with a Leader"
        subdir = os.path.join(m["start_time"], m["topic"])
        os.makedirs(subdir, mode=0o755, exist_ok=True)

        # Get URLs for the download URLs for that meeting
        for recording in m['recording_files']:
            print("    %s (%s): %s?access_token=%s"
                  % (recording['file_type'],
                     prettysize(recording['file_size']),
                     recording['download_url'],
                     JWT_TOKEN))

            if not fetch:
                continue

            ext = recording["file_extension"].lower()
            filepath = os.path.join(subdir, "zoom."+ext)

            if not os.path.exists(filepath):
                print("    %s (%s): %s?access_token=%s"
                      % (recording['file_type'],
                         prettysize(recording['file_size']),
                         recording['download_url'],
                         JWT_TOKEN))
                url = recording["download_url"]
                if ext in ['txt', 'vtt']:
                    print("Trying to fetch", url)
                    r1 = requests.get(url,
                                      headers=AUTHORIZATION_HEADER)
                    with open(filepath, "wb") as outfile:
                        outfile.write(r1.content)
                    os.chmod(filepath, 0o444)
                else:
                    print("Calling yt-dlp")
                    subprocess.call(["yt-dlp", "-o", filepath,
                                     url + "?access_token="+JWT_TOKEN],
                                    shell=False)

    if not fetch:
        print("\nNothing downloaded: specify a base directory to fetch to")


def prettysize(nbytes):
    print(nbytes, type(nbytes))
    if nbytes < 1000: return "%d b" % (nbytes)
    if nbytes < 1000000: return "%d K" % (nbytes / 1000)
    return "%d M" % (nbytes / 1000000)


if __name__ == '__main__':
    # First (and only) argument is a base directory into which to download
    if len(sys.argv) == 2:
        os.chdir(sys.argv[1])
        show_zoom_recordings(fetch=True)

    else:
        show_zoom_recordings(fetch=False)
