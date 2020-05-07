#!/usr/bin/env python

# A quickie way to switch audio between internal speakers and a USB hub,
# using pulseaudio commandline tools.

# Adjust as needed for your specific audio devices.
# To see your available audio devices: pacmd list-cards
# For each card, look under "profiles:"

import sys
import subprocess

# If python-termcolor is installed, show muted items in red.
try:
    from termcolor import colored
    def mutedstring(s):
        return colored(s, 'red')
except:
    def mutedstring(s):
        return f'  ({s})'

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


def parse_volume(words):
    if words[1] == b'front-left:':
        return [int(words[2]), int(words[9])]
    if words[1] == b'mono:':
        return [int(words[2])]
    print("Can't parse volume line:", words)
    return None


def after_equals(line):
    eq = line.index(b'=')
    if not eq:
        return None
    ret =line[eq+1:].strip().decode()
    if ret.startswith('"') and ret.endswith('"'):
        ret = ret[1:-1]
    return ret.strip()


by_index = { 'source': {}, 'sink': {} }


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
            curdict['index'] = words[1].decode()
            by_index[whichtype][curdict['index']] = curdict

        elif words[0] == b'name:':
            # Take the second word and remove enclosing <>
            curdict['name'] = words[1][1:-1].decode()

        elif words[0] == b'muted:':
            curdict['muted'] = (words[1] == b'yes')

        elif words[0] == b'volume:':
            curdict['volume'] = parse_volume(words)

        elif words[0] == b'base' and words[1] == b'volume:':
            curdict['base_volume'] = int(words[2])

        elif len(words) >= 2 and words[1] == b'=' \
             and words[0] in [b'alsa.long_card_name',
                              b'device.product.name',
                              b'device.description']:
            name = after_equals(line)
            curdict[words[0].decode()] = name

    if curdict:
        devs.append(curdict)
    return devs


def parse_sink_inputs():
    """Parse sink inputs: running programs that are producing audio.
    """
    cmd = ['pactl', 'list', 'sink-inputs']
    sink_inputs = []
    sink_input = None
    for line in subprocess.check_output(cmd).split(b'\n'):
        if line.startswith(b'Sink Input'):
            if sink_input:
                sink_inputs.append(sink_input)
            sink_input = {}
            continue

        words = line.strip().split()
        if not words:
            continue

        if words[0] == b'Sink:':
            sink_input['sink'] = words[1].decode()

        if words[0] == b'media.name':
            sink_input['medianame'] = after_equals(line)
        if words[0] == b'application.name':
            sink_input['appname'] = after_equals(line)

        if words[0] == b'Mute':
            sink_input['mute'] = (words[1] != b'No')

        if words[0] == b'Volume':
            sink_input['volume'] = parse_volume(words)

    if sink_input:
        sink_inputs.append(sink_input)
    return sink_inputs


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
        out = mutedstring(out)

    return out


def sink_input_str(sidict):
    # return str(sidict)
    return f"{sidict['appname']} {sidict['medianame']} ({sidict['sink']})" \
        f" --> {by_index['sink'][sidict['sink']]['device.description']}"


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

        sink_inputs = parse_sink_inputs()
        print('Sink Inputs:')
        for si in sink_inputs:
            print(sink_input_str(si))

