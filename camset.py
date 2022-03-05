#!/usr/bin/env python3

# v4l settings useful for a Logitech c920 that keeps disconnecting
# and so needing to be reset every few minutes.

'''
Alwyas:
v4l2-ctl -d /dev/video2 --set-ctrl focus_automatic_continuous=0

Day:
v4l2-ctl -d /dev/video2 --set-ctrl white_balance_automatic=1
v4l2-ctl -d /dev/video2 --set-ctrl brightness=128

Night:
v4l2-ctl -d /dev/video2 --set-ctrl white_balance_automatic=0
v4l2-ctl -d /dev/video2 --set-ctrl white_balance_temperature=2500
v4l2-ctl -d /dev/video2 --set-ctrl brightness=300

Nop:
v4l2-ctl -d /dev/video2 --get-ctrl backlight_compensation=1
'''

from collections import OrderedDict   # for python < 3.7
import subprocess
import re
import sys, os

day_settings = OrderedDict({
    "focus_automatic_continuous": "0",
    "white_balance_automatic": "1",
    "auto_exposure": "3",
    "brightness": "150",
})

night_settings = OrderedDict({
    "focus_automatic_continuous": "0",
    "white_balance_automatic": "0",
    "white_balance_temperature": "2500",
    "brightness": "300",
    "auto_exposure": "0",
    "exposure": "120",
})


def run_it(args):
    print("Running:", args)
    try:
        subprocess.run(args)
    except:
        print("Couldn't run", args)


def find_camera(pat:str, allcams:dict) -> str:
    """Return the video device (/dev/videoN) associated with the
       first camera whose name contains the given pattern (case insensitive).
    """
    pat = pat.lower()
    for cam in allcams:
        if pat in cam.lower():
            return allcams[cam][0]
    return None


def find_all_cameras() -> dict:
    """Build a dict of available v4l devices:
       { camname: [ dev0 dev1 ... ]
    """
    found_cameras = {}

    devs = subprocess.run(["v4l2-ctl", "--list-devices"],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL).stdout
    devs = devs.splitlines()

    cam = None
    for line in devs:
        line = line.decode('utf-8')
        # print("::", line)
        if line.startswith('\t'):
            # Inside a camera section are three /dev/videoN lines.
            # For now, take the first one.
            if cam:
                # print("Appending", line.strip(), "to", cam)
                found_cameras[cam].append(line.strip())
            continue

        line = line.strip()
        if not line:
            continue

        if line != cam:
            cam = line
            # print("New cam", cam)
            found_cameras[cam] = []

    return found_cameras


def get_settings(videodev:str) -> dict:
    ctrls = {}
    ctrl_lines = subprocess.run(["v4l2-ctl", "-d", videodev, "--list-ctrls"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL).stdout
    ctrl_lines = ctrl_lines.decode('utf-8').splitlines()
    for line in ctrl_lines:
        line = line.strip()
        match = re.match(' *([a-zA-Z_]*) 0x[0-9a-f]{8} .*: ([a-zA-Z_= 0-9]+)',
                         line)
        if not match:
            continue
        cname = match.group(1)
        pairs = match.group(2).split(' ')
        vals = {}
        for pair in pairs:
            if not pair:
                continue
            try:
                pair = pair.split('=')
                # XXX consider converting pair[1] to an int
                vals[pair[0]] = pair[1]
            except:
                print("Couldn't split", pair)

        ctrls[cname] = vals

    return ctrls


def set_settings(videodev:str, mode:str):
    if mode == "day":
        settings = day_settings
    elif mode == "night":
        settings = night_settings
    else:
        raise RuntimeError("Don't know mode", mode)

    for setting in settings:
        run_it(["v4l2-ctl", "-d", videodev, "--set-ctrl",
                f"{setting}={settings[setting]}"])


if __name__ == '__main__':
    def Usage():
        print(f"Usage: {os.path.basename(sys.argv[0])} camname profile")
        print(f"e.g. {os.path.basename(sys.argv[0])} logitech night")
        sys.exit(0)


    if len(sys.argv) > 1:
        pat = sys.argv[1]
        if pat == '-h' or pat == '--help':
            Usage()
    else:
        pat = None

    all_cameras = find_all_cameras()
    keys = list(all_cameras.keys())

    if len(all_cameras) == 1:
        camdev = all_cameras[keys[0]][0]
    elif pat:
        camdev = find_camera(pat, all_cameras)
    else:
        camdev = None

    if not camdev:
        print("Please specify which camera you want:")

        for cam in all_cameras:
            print(cam)
            print("   ", ' '.join(all_cameras[cam]))
        sys.exit(0)

    print("Camera dev:", camdev)

    if len(sys.argv) == 3:
        set_settings(camdev, sys.argv[2])

    camsettings = get_settings(camdev)
    for setting in camsettings:
        print(f"{setting:>27}: ", end='')
        if 'value' in camsettings[setting]:
            print(f"{camsettings[setting]['value']:4} ", end='')
        else:
            print("     ", end='')
        print(" (", end='')
        for key in camsettings[setting]:
            if key == 'value':
                continue
            print(f" {key}={camsettings[setting][key]}", end='')
        print(" )")

