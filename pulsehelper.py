#!/usr/bin/env python

# A quickie way to switch audio between internal speakers and a USB hub,
# using pulseaudio commandline tools.

# Configure your specific audio devices in ~/.config/pulsehelper/config.
# To see your available audio devices: pacmd list-cards
# For each card, look under "profiles:"
# See mics: pacmd list-sources; sinks: pacmd list_sinks

# Uses the termcolor module if it's available to highlight fallbacks
# and muted devices.

import sys, os
import subprocess
import re

# The configuration, if any, is global.
config = {}

DEBUG = False

# Hide monitor inputs?
HIDE_MONITORS = True


# If python-termcolor is installed, show muted items in red.
try:
    from termcolor import colored
    def mutedstring(s):
        return colored(s, 'red')
    def fallbackstring(s):
        return colored(s, 'green', attrs=['bold'])
    def monitorstring(s):
        return colored(s, 'yellow')
except:
    def mutedstring(s):
        return f'  ({s})'
    def fallbackstring(s):
        return '** ' + s
    def monitorstring(s):
        return s + ' ((fallback))'

def parse_cards() -> list:
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


def parse_volume(words: list) -> int:
    if words[1] == b'front-left:':
        return [int(words[2]), int(words[9])]
    if words[1] == b'mono:':
        return [int(words[2])]
    print("Can't parse volume line:", words)
    return None


def after_equals(line: bytes) -> str:
    eq = line.index(b'=')
    if not eq:
        return None
    ret =line[eq+1:].strip().decode()
    if ret.startswith('"') and ret.endswith('"'):
        ret = ret[1:-1]
    return ret.strip()


by_index = { 'source': {}, 'sink': {} }


def parse_sources_sinks(whichtype: str) -> list:
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

        elif words[0] == b'volume' and words[1] == b'steps:':
            curdict['volsteps'] = int(words[2])

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

        elif line.startswith(b"active port:"):
            curdict["active port"] = b' '.join(words[2:]).decode()

    if curdict:
        devs.append(curdict)
    return devs


def parse_sink_inputs() -> list:
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


def mute_unmute(mute: bool, dev: dict, devtype: str):
    """Mute (mute=True) or unmute (False) a source (devtype="source")
       or sink ("sink") of a given name.
       pactl set-source-mute $source 1
    """
    args = ["pactl", f"set-{devtype}-mute", dev['name'],
            '1' if mute else '0']
    if DEBUG:
        print("muting" if mute else "unmuting",
              sub_str(dev['device.description']),
              "=", dev['device.description'],
              "=", dev["name"])
        print("Calling:", args)
    subprocess.call(args)


def mute_all(devtype: str):
    if DEBUG:
        print("Muting all")

    for i, dev in enumerate(parse_sources_sinks(devtype)):
        # Don't check for monitors, mute them too.
        mute_unmute(True, dev, devtype)


def match_dev_pattern(pattern: str, devtype: str, devs: list) -> int:
    """Find the device matching pattern, which could be a nickname,
       an integer, a full match for a dev name, or a partial match
       for a dev name if there's only one such match.
       return devindex or -1.
    """
    # Is pattern a sub?
    for sub in config["subs"]:
        # sub is a tuple: the first item is the real device name,
        # the rest are nicknames.
        # If any of the nickname matches pattern,
        # replace pattern with the real device name.
        if pattern in sub[1:]:
            devname = sub[0]
            for i, dev in enumerate(devs):
                if devname == dev["device.description"]:
                    return i
            print(f"{pattern} matched nonexistent device {devname}")

    # Pattern isn't a sub
    # Is it an integer, to be used as an index?
    # try:
    #     patternint = int(pattern)
    #     if patternint < len(devs):
    #         print("Returning patternint", patternint)
    #         return patternint

    # except ValueError:
    #     pass    # Not an index

    # See if pattern is an exact match for a device
    for i, dev in enumerate(devs):
        # Is it a monitor, and are monitors hidden?
        if is_monitor(dev) and HIDE_MONITORS:
            continue

        if pattern == dev["index"]:
            print("Returning", dev)
            return i
        if pattern == dev["device.description"]:
            return i

    # See if pattern is an partial match for any devices
    partials = []
    for i, dev in enumerate(devs):
        if pattern in dev["device.description"]:
            partials.append(i)
        else:
            print(f'{pattern} not in {dev["device.description"]}')
    if len(partials) == 1:
        return partials[0]
    if len(partials) > 1:
        print(f"{pattern} matched more than one device:")
        for i in partials:
            print("   ", devs[i]["device.description"])

    return -1


def unmute_one(pattern: str, devtype: str, mute_others: bool = True):
    """Make one source or sink the active fallback, unmuting it and
       (optionally) muting all others.
       pattern is a string (not regexp) to search for in the device description,
       e.g. "USB" or "HDMI1", or an integer or a string representing an int.
       devtype is "source" or "sink".
       If pattern is None or none, mute everything of that type.
    """

    if pattern.lower() == "none":
        mute_all(devtype)
        return

    devs = parse_sources_sinks(devtype)

    devindex = match_dev_pattern(pattern, devtype, devs)
    if devindex < 0:
        print("No match")
        sys.exit(1)

    if devindex < 0:
        print(f"Didn't find a {devtype} matching '{pattern}'")
        return

    # Now devindex should be set.
    # Set the given device as the fallback
    if DEBUG:
        print("Setting", sub_str(devs[devindex]['device.description']),
              "=", devs[devindex]['device.description'],
              "as fallback")
        print("Calling", ["pactl", f"set-default-{devtype}",
                          devs[devindex]['index']])
    subprocess.call(["pactl", f"set-default-{devtype}",
                     devs[devindex]['index']])

    for i, dev in enumerate(devs):
        if i == devindex:
            mute_unmute(False, dev, devtype)
        elif mute_others:
            mute_unmute(True, dev, devtype)

    if DEBUG:
        print()


def sub_str(s: str) -> str:
    """Substitute any matches found in config['subs'].
    """
    if 'subs' not in config:
        return s

    for pair in config['subs']:
        if pair[0] == s:
            s = s.replace(pair[0], pair[1])

    return s


def is_monitor(devdict: dict) -> bool:
    if 'monitor' in devdict['name'].lower():
        return True
    if 'monitor' in devdict['device.description'].lower():
        return True
    return False


def sink_or_source_str(devdict: dict) -> str:
    """Pretty output for a sink or source.
    """
    # from pprint import pprint
    # pprint(devdict)
    # print("----")

    substr = sub_str(devdict['device.description'])
    out = f"{devdict['index']}: {substr}"

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

    if "active port" in devdict:
        out += f" (port: {devdict['active port']})"

    if devdict['muted']:
        out += ' (MUTED)'

    # Monitor and muted are both colorized, so they're mutually exclusive
    if is_monitor(devdict):
        if HIDE_MONITORS:
            return ''
        out = monitorstring(out)
    elif devdict['muted']:
        out = mutedstring(out)

    # fallbackstring is bold, so it can coexist with either color
    if devdict['fallback']:
        out = fallbackstring(out)

    if substr != devdict['device.description']:
        out += f"\n   = {devdict['device.description']}"

    return out


def sink_input_str(sidict: dict) -> str:
    """Pretty output for a sink input.
    """
    # return str(sidict)
    out = f"{sidict['appname']} {sidict['medianame']} --> "

    sink = by_index['sink'][sidict['sink']]
    out += f"{sub_str(sink['device.description'])}"

    if sink['muted']:
        out = mutedstring(out)

    return out


def read_config_file() -> dict:
    """Read the config file.
       Currently, the only configuration is a list of substitutions
       to make the output shorter and more readable.
    """
    global config

    with open(os.path.expanduser("~/.config/pulsehelper/config")) as fp:
        for line in fp:
            # Strip whitespace and comments
            line = re.sub('\s*#.*$', '', line.strip())
            if not line:
                continue
            if line.startswith('#'):
                continue
            parts = [ p.strip() for p in line.split('=') ]
            if len(parts) != 2:
                print("Config file parse error, line:", line)
                continue
            if 'subs' not in config:
                config['subs'] = []
            config['subs'].append((parts[1], parts[0]))

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
        s = sink_or_source_str(sink)
        if (s): print(s)
    print()

    sources = parse_sources_sinks('source')
    print('Sources:')
    for source in sources:
        s = sink_or_source_str(source)
        if (s): print(s)
    print()

    sink_inputs = parse_sink_inputs()
    print('Currently running (sink inputs):')
    for si in sink_inputs:
        print(sink_input_str(si))
    else:
        print("None")


def active_sink() -> dict:
    """Return the active sink, or None
    """
    for sink in parse_sources_sinks('sink'):
        if sink['fallback']:
            return sink
    return None


def get_sink_volume(sink: dict = None) -> tuple:
    """Get volume on a sink (if None, use the active sink).
       Returns a list of channel volumes and the base volume
       (the volume that's considered to be 100%, though sinks
       can have volume set above this)
       e.g. [56360, 56360], 65536
    """
    if not sink:
        sink = active_sink()
    if not sink:
        return -1

    if 'muted' in sink:
        muted = sink['muted']
        if muted:
            return 0
    else:
        muted = False

    return sink['volume'], sink['base_volume']


def volume_string(sink: dict = None) -> str:
    """Return a readable string showing volume settings and percentages.
    """
    vol, basevol = get_sink_volume(sink)
    s = str( [ v for v in vol ] )
    s += " / "
    s += str(basevol)
    s += "    "
    s += str( [ int(round(v * 100 /basevol)) for v in vol ] )
    return s


def set_sink_volume(percent: int, sink: dict = None, direction: int = 0):
    """Set volume on a sink.
       newvol is an int percentage between 0 and 100.
       sink is a dictionary; if None, use the active sink.
       If direction is nonzero, adjust the current volume
       in that direction by the given percent.

       May not set to an exact value: pactl seems to take
       set-sink-volume arguments as only approximate hints.
    """
    if not sink:
        sink = active_sink()
    if not sink:
        print("No active sink")
        return

    # if 'base_volume' not in sink:
    #     print("No base_volume, using percent")
    #     subprocess.call(["pactl", "set-sink-volume", "@DEFAULT_SINK@",
    #                      "%d%%" % newvol])
    #     return

    basevol = int(sink['base_volume'])
    maxvol = max(get_sink_volume(sink)[0])

    # Current volume in percent
    curvol = int(round(maxvol * 100 / basevol))

    if direction > 0:
        newvol = curvol + percent

    elif direction < 0:
        newvol = curvol - percent

    else:
        newvol = percent

    volnum = int(newvol * basevol / 100.)

    if max(sink['volume']) >= basevol:
        pass

    if DEBUG:
        print("Current volume %d = %d%%; new volume will be %d + %d%%"
              % (maxvol, curvol, newvol, volnum))
    subprocess.call(["pactl", "set-sink-volume", "@DEFAULT_SINK@",
                     str(volnum)])


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
    parser.add_argument('--setvol', action='store', type=str, dest='setvol',
                        help='Set the current volume level for the active sink.'
                             ' A percentage, optionally preceded by + or -.')
    parser.add_argument('--show-monitors', action='store_true',
                        dest='show_monitors',
                        help='Show monitor sources (hidden by default)')
    parser.add_argument('-d', '--debug', action='store_true', dest='debug',
                        help='Show debugging chatter')
    parser.add_argument('-q', '--quiet',
                        action="store_true", dest="force_quiet",
                        help="Don't print status at the end")
    args = parser.parse_args(sys.argv[1:])

    config = read_config_file()

    if args.debug:
        DEBUG = True

    HIDE_MONITORS = not(args.show_monitors)

    quiet = False

    if args.getvol:
        print(volume_string())
        quiet = True

    if args.setvol:
        sink = active_sink()
        if sink:
            if args.setvol[0] == '-':
                direc = -1
                setvol = int(args.setvol[1:])
            elif args.setvol[0] == '+':
                direc = 1
                setvol = int(args.setvol[1:])
            else:
                direc = 0
                setvol = int(args.setvol)

            set_sink_volume(setvol, sink, direction=direc)

            # To get the new volume, need to re-fetch the device,
            # so don't specify the sink here.
            print("New volume:", volume_string())

        else:
            print("No active sink")

        quiet = True

    if args.source:
        unmute_one(args.source, 'source')
        quiet = False

    if args.sink:
        unmute_one(args.sink, 'sink')
        quiet = False

    if not quiet and not args.force_quiet:
        print_status()

