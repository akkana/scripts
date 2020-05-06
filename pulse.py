#!/usr/bin/env python

# A quickie way to switch audio between internal speakers and a USB hub,
# using pulseaudio commandline tools.

# Adjust as needed for your specific audio devices.
# To see your available audio devices: pacmd list-cards
# For each card, look under "profiles:"

#
# SOME PULSEAUDIO NOTES:
#
# https://brokkr.net/2018/05/24/down-the-drain-the-elusive-default-pulseaudio-sink/
# has some great info on pulseaudio fallbacks:
# pacmd list-sinks | grep -e 'name:' -e 'index'
# puts an asterisk in front of the fallback.
# There are also some  old comments claiming that you can
# export PULSE_SINK="sink_name"
# export PULSE_SOURCE="source_name"
# Get the names with
# LANG=C pactl list | grep -A3 'Sink #'
# then, e.g.,
#   PULSE_SINK='alsa_output.usb-0c76_USB_PnP_Audio_Device-00.analog-stereo' musicplayer
#   PULSE_SINK='alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__sink' musicplayer
# In theory, Set the default by noting the index of the sink you want, then
#   pacmd set-default-sink 1
# In practice that doesn't work. Maybe it would after editing
# /etc/pulse/default.pa to set:
#   load-module module-stream-restore restore_device=false
#
# Change a running stream to a different sink:
#   pacmd list-sink-inputs
#   pacmd move-sink-input 5 1

import sys
import subprocess

def parse_cards():
    """Get a list of cards"""
    cards = []
    internal_card = None
    usb_card = None
    for line in subprocess.check_output(['pactl', 'list',
                                         'short', 'cards']).split(b'\n'):
        if line:
            card = line.split()[1].decode()
            cards.append(card)
            if '.usb' in card:
                usb_card = card
            elif '.pci' in card:
                internal_card = card
    return cards

def parse_sources_sinks(whichtype):
    """Get a list of sinks or sources. whichtype should be "source" or "sink".
    """
    devs = []
    curdict = None
    cmd = ['pacmd', f'list-{whichtype}s']
    for line in subprocess.check_output(cmd).split(b'\n'):
        line = line.strip()
        try:
            words = line.split()
        except:
            continue
        if not words:
            continue

        if words[0] == b'*':         # default/fallback
            fallback = True
            words = words[1:]
        else:
            fallback = False

        if words[0] == b'index:':    # start a new sink
            if curdict:
                devs.append(curdict)
            curdict = { 'fallback': fallback }

        elif words[0] == b'name:':
            # Take the second word and remove enclosing <>
            curdict['name'] = words[1][1:-1].decode()

        elif words[0] == b'muted:':
            curdict['muted'] = (words[1] == 'yes')

        elif words[0] == b'volume:':
            if words[1] == b'front-left:':
                curdict['volume'] = [int(words[2]), int(words[9])]
            elif words[1] == b'mono:':
                curdict['volume'] = [int(words[2])]
            else:
                print("Can't parse volume line:", words)

        elif words[0] == b'base' and words[1] == b'volume:':
            curdict['base_volume'] = int(words[2])

        elif len(words) >= 2 and words[1] == b'=' \
             and words[0] in [b'alsa.long_card_name',
                              b'device.product.name',
                              b'device.description']:
            name = ' '.join([w.decode() for w in words[2:]])
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            curdict[words[0].decode()] = name

    if curdict:
        devs.append(curdict)
    return devs


def mute_unmute(mute, devname, devtype):
    """Mute (mute=True) or unmute (False) a source (devtype="source")
       or sink ("sink") of a given name.
       pactl set-source-mute $source 1
    """
    print("muting" if mute else "unmuting", devname)
    subprocess.call(["pactl", f"set-{devtype}-mute", devname,
                     '1' if mute else '0'])


def unmute_one(pattern, devtype, mute_others=True):
    """Make one source or sink active, unmuting it and
       (optionally) muting all others.
       pattern is a string (not regexp) to search for in the device description,
       e.g. "USB" or "HDMI1".
       devtype is "source" or "sink".
       If pattern is None or none, mute everything of that type.
    """
    devs = parse_sources_sinks(devtype)
    devindex = -1
    muteall = (pattern.lower() == "none")

    # Make sure there's a match before muting anything
    if not muteall:
        for i, dev in enumerate(devs):
            if pattern in dev['device.description']:
                devindex = i
                break

        if devindex < 0:
            print(f"Didn't find a {devtype} matching", pattern)
            return

    for dev in devs:
        if not muteall and pattern in dev['device.description']:
            mute_unmute(False, dev['name'], devtype)
        elif mute_others:
            mute_unmute(True, dev['name'], devtype)


def sink_str(devdict):
    out = devdict['device.description']
    if devdict['fallback']:
        out += ' (--FALLBACK--)'
    if 'volume' in devdict:
        try:
            multiplier = float(devdict['base_volume']) / 65536.
        except:
            multiplier = 1.
        out += ' (' + ', '.join([ str(int(v / 655.36 * multiplier))
                                  for v in devdict['volume']]) + ')'
    else:
        out += ' (volume unknown)'
    if devdict['muted']:
        out += ' (MUTED)'
    return out


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="""Control PulseAudio devices.

Provide patterns matching source or sink arguments, e.g.
--sink USB will unmute any sink that has "USB" in its description.
Use none to mute every source or every sink.

With no arguments, prints all cards, sources and sinks.
""",
                             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--source', action="store", dest="source",
                        help='Set current source (microphone)')
    parser.add_argument('--sink', action="store", dest="sink",
                        help='Set current sink (speaker)')
    args = parser.parse_args(sys.argv[1:])


    if args.source:
        unmute_one(args.source, 'source')
    elif args.sink:
        unmute_one(args.sink, 'sink')
    else:
        cards = parse_cards()
        print("Cards:")
        for card in cards:
            print(card)
        print()

        sinks = parse_sources_sinks('sink')
        print('Sinks:')
        for sink in sinks:
            print(sink_str(sink))
        print()

        sources = parse_sources_sinks('source')
        print('Sources:')
        for source in sources:
            print(sink_str(source))
        print()

