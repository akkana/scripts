#!/usr/bin/env python

# A quickie way to switch audio between internal speakers and a USB hub,
# using pulseaudio commandline tools.

# Adjust as needed for your specific audio devices.
# To see your available audio devices: pacmd list-cards
# For each card, look under "profiles:"

# Uses the termcolor module if it's available to highlight fallbacks
# and muted devices.

import sys, os
import subprocess

# The configuration, if any, is global.
config = {}

DEBUG = False


# If python-termcolor is installed, show muted items in red.
try:
    from termcolor import colored
    def mutedstring(s):
        return colored(s, 'red')
    def fallbackstring(s):
        return colored(s, 'green', attrs=['bold'])
except:
    def mutedstring(s):
        return f'  ({s})'
    def fallbackstring(s):
        return '** ' + s

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


def mute_unmute(mute, dev, devtype):
    """Mute (mute=True) or unmute (False) a source (devtype="source")
       or sink ("sink") of a given name.
       pactl set-source-mute $source 1
    """
    args = ["pactl", f"set-{devtype}-mute", dev['name'],
            '1' if mute else '0']
    if DEBUG:
        print("muting" if mute else "unmuting",
              sub_str(dev['device.description']))
        print("Calling:", args)
    subprocess.call(args)


def unmute_one(pattern, devtype, mute_others=True):
    """Make one source or sink the active fallback, unmuting it and
       (optionally) muting all others.
       pattern is a string (not regexp) to search for in the device description,
       e.g. "USB" or "HDMI1", or an integer or a string representing an int.
       devtype is "source" or "sink".
       If pattern is None or none, mute everything of that type.
    """
    devs = parse_sources_sinks(devtype)
    muteall = (pattern.lower() == "none")
    devindex = -1

    try:
        patternint = int(pattern)

        for i, dev in enumerate(devs):
            if dev["index"] == pattern:
                devindex = i
                break

    except ValueError:
        if not muteall:
            # Make sure there's a match before muting anything
            devindex = -1
            for i, dev in enumerate(devs):
                if pattern in sub_str(dev['device.description']):
                    devindex = i
                    break
                if pattern in dev['device.description']:
                    devindex = i
                    break

            if devindex < 0:
                print(f"Didn't find a {devtype} matching", pattern)
                return

    # Now either muteall or devindex should be set.
    # Set the given device as the fallback
    if not muteall and devindex >= 0:
        if DEBUG:
            print("Setting", sub_str(devs[devindex]['device.description']),
                  "as fallback")
            print("Calling", ["pactl", f"set-default-{devtype}",
                              devs[devindex]['index']])
        subprocess.call(["pactl", f"set-default-{devtype}",
                         devs[devindex]['index']])

    for i, dev in enumerate(devs):
        if not muteall and i == devindex:
            mute_unmute(False, dev, devtype)
        elif mute_others:
            mute_unmute(True, dev, devtype)

    if DEBUG:
        print()


def sub_str(s):
    """Substitute any matches found in config['subs'].
    """
    if 'subs' not in config:
        return s

    for pair in config['subs']:
        if pair[0] in s:
            s = s.replace(pair[0], pair[1])

    return s


def sink_or_source_str(devdict):
    """Pretty output for a sink or source.
    """
    out = f"{devdict['index']}: {sub_str(devdict['device.description'])}"

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
    if devdict['fallback']:
        out = fallbackstring(out)

    return out


def sink_input_str(sidict):
    """Pretty output for a sink input.
    """
    # return str(sidict)
    out = f"{sidict['appname']} {sidict['medianame']} --> "

    sink = by_index['sink'][sidict['sink']]
    out += f"{sub_str(sink['device.description'])}"

    if sink['muted']:
        out = mutedstring(out)

    return out


def read_config_file():
    """Read the config file.
       Currently, the only configuration is a list of substitutions
       to make the output shorter and more readable.
    """
    global config
    try:
        with open(os.path.expanduser("~/.config/pulsehelper/config")) as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                parts = [ p.strip() for p in line.split('=') ]
                if len(parts) != 2:
                    print("Config file parse error, line:", line)
                    continue
                if 'subs' not in config:
                    config['subs'] = []
                config['subs'].append((parts[1], parts[0]))

    except:
        pass

    return config


def print_status():
    """Print all the known inputs, outputs and processes and their stati.
    """
    cards = parse_cards()
    print("Cards:")
    for card in cards:
        print(card)
    print()

    sinks = parse_sources_sinks('sink')
    print('Sinks:')
    for sink in sinks:
        print(sink_or_source_str(sink))
    print()

    sources = parse_sources_sinks('source')
    print('Sources:')
    for source in sources:
        print(sink_or_source_str(source))
    print()

    sink_inputs = parse_sink_inputs()
    print('Currently running (sink inputs):')
    for si in sink_inputs:
        print(sink_input_str(si))


def get_active_sink_volume():
    for sink in parse_sources_sinks('sink'):
        if not sink['fallback']:
            continue
        if 'muted' in sink:
            muted = sink['muted']
        else:
            muted = False
        return int(sink['base_volume']), muted

    return -1

def set_active_sink_volume(newvol):
    if '%' not in newvol:
        newvol += '%'
        subprocess.call(["pactl", "set-sink-volume", "@DEFAULT_SINK@",
                         newvol])


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="""Control PulseAudio devices.

Provide patterns matching source or sink arguments, e.g.
--sink USB will unmute any sink that has "USB" in its description.
Or specify the number of the source or sink.
Use none to mute every source or every sink.

With no arguments, prints all cards, sources and sinks.

You can create a ~/.config/pulsehelper/config file to provide shorter names.
Lines in that file should look like:
Super Long Hard To Read PulseAudio Name = Nice Short Name
""",
                             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--source', action="store", dest="source",
                        help='Set current source (microphone)')
    parser.add_argument('--sink', action="store", dest="sink",
                        help='Set current sink (speaker)')
    parser.add_argument('--getvol', action='store_true', dest='getvol',
                        help='Get the current volume level for the active sink')
    parser.add_argument('-d', '--debug', action='store_true', dest='debug',
                        help='Get the current volume level for the active sink')
    parser.add_argument('--setvol', action='store', type=str, dest='setvol',
                        default=-1,
                        help='Set the current volume level for the active sink.'
                             ' A percentage, optionally preceded by + or -.')
    parser.add_argument('-q', '--quiet',
                        action="store_true", dest="force_quiet",
                        help="Don't print status at the end")
    args = parser.parse_args(sys.argv[1:])

    config = read_config_file()

    if args.debug:
        DEBUG = True

    quiet = False

    if args.getvol:
        print(get_active_sink_volume())
        quiet = True

    if args.setvol >= 0:
        print(set_active_sink_volume(args.setvol))
        quiet = True

    if args.source:
        unmute_one(args.source, 'source')
        quiet = False

    if args.sink:
        unmute_one(args.sink, 'sink')
        quiet = False

    if not quiet and not args.force_quiet:
        print_status()

