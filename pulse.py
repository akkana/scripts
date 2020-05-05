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
from pprint import pprint

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
    for line in subprocess.check_output(['pacmd',
                                         f'list-{whichtype}s']).split(b'\n'):
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
            curdict['name'] = line.split()[1][1:-1].decode()

        elif words[0] == b'muted:':
            curdict['muted'] = (line.split()[1] == 'yes')

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


def set_sink(newsink, mute_others=True):
    sinks = parse_sources_sinks('sink')
    sinkindex = -1
    # Make sure there's a match before muting anything
    for i, sink in enumerate(sinks):
        if newsink in sink['device.description']:
            sinkindex = i
            break

    if sinkindex < 0:
        print("Didn't find a sink matching", newsink)
        return

    for sink in sinks:
        if newsink in sink['device.description']:
            mute_unmute(False, sink['name'], 'sink')
        elif mute_others:
            mute_unmute(True, sink['name'], 'sink')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Control PulseAudio devices")
    parser.add_argument('--source', action="store", dest="source",
                        help='Set current source (microphone)')
    parser.add_argument('--sink', action="store", dest="sink",
                        help='Set current sink (speaker)')
    args = parser.parse_args(sys.argv[1:])


    if args.source:
        print("Can't set source yet")
    elif args.sink:
        set_sink(args.sink)
    else:
        cards = parse_cards()
        print("Cards:")
        for card in cards:
            print(card)
        print()

        sinks = parse_sources_sinks('sink')
        print('Sinks:')
        for sink in sinks:
            print(sink['device.description'])
        print()

        sources = parse_sources_sinks('source')
        print('Sources:')
        for source in sources:
            print(source['device.description'])
        print()



'''
internal_i=$(pactl list short cards | grep pci | awk '{ print $1 }')
hub_i=$(pactl list short cards | grep USB_PnP_Audio_Device | awk '{ print $1 }')

if [[ $1 == 'hub' ]]; then
    echo "Directing audio to USB hub"
    pactl set-card-profile $internal_i off
    if [[ ! -z $hub_i ]]; then
        pactl set-card-profile $hub_i output:analog-stereo
    fi

elif [[ $1 == 'hubmic' ]]; then
    echo "Directing audio to USB hub with mic enabled"
    pactl set-card-profile $internal_i off
    if [[ ! -z $hub_i ]]; then
        pactl set-card-profile $hub_i output:analog-surround-40+input:analog-stereo
    fi

elif [[ $1 == 'int' ]]; then
    echo "Directing audio to internal speakers"
    if [[ ! -z $hub_i ]]; then
        pactl set-card-profile $hub_i off
    fi
    # Carbon X1 on Ubuntu eoan:
    # pactl set-card-profile $internal_i output:analog-stereo
    # Carbon X1 on Ubuntu fossa:
    pactl set-card-profile $internal_i HiFi

elif [[ $1 == 'intmic' ]]; then
    echo "Directing audio to internal speakers with mic enabled"
    if [[ ! -z $hub_i ]]; then
        pactl set-card-profile $hub_i off
    fi
    # Carbon X1 on Ubuntu eoan:
    pactl set-card-profile $internal_i output:analog-surround-40+input:analog-stereo
    # Carbon X1 on Ubuntu fossa:
    pactl set-card-profile $internal_i HiFi

else
    echo 'Usage: pulse [hub|int|hubmic|intmic]'
fi
'''
