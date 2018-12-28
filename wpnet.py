#!/usr/bin/env python3

# A wrapper script to make it easier to use wpa_cli to connect.
# https://wiki.archlinux.org/index.php/WPA_supplicant#Connecting_with_wpa_cli
# was very helpful.
# Copyright 2018 by Akkana Peck: share and enjoy under the GPLv2 or later.

import subprocess
import os, sys
import argparse
import getpass
import time

verbose=True

def run_as_root(cmdargs):
    '''Run cmdargs inside sudo, unless we're already root.
       return (stdout, stderr) as strings.
    '''
    if os.getpid() != 0:
        cmdargs = ["sudo"] + cmdargs

    if verbose:
        print("** Run:", ' '.join(cmdargs))
    proc = subprocess.Popen(cmdargs, shell=False,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # proc.communicate() returns bytes, so change them to strings:
    return ( b.decode() for b in proc.communicate() )

def start_wpa_supplicant(iface):
    # https://wiki.archlinux.org/index.php/WPA_supplicant
    if is_wpa_running():
        if verbose:
            print("wpa_supplicant is already running")
        return
    if verbose:
        print("Starting wpa_supplicant ...", end='')
    subprocess.call(['sudo', 'wpa_supplicant', '-B', '-i', iface,
                     '-c', '/etc/wpa_supplicant/wpa_supplicant.conf'])
    time.sleep(5)

def is_wpa_running():
    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]

    for pid in pids:
        try:
            args = open(os.path.join('/proc', pid, 'cmdline'),
                        'rb').read().decode().split('\0')
            if args[0] == 'wpa_supplicant':
                return True
        except IOError: # proc has already terminated
            continue

    return False

def start_dhcp(iface):
    if verbose:
        print("Starting dhcp")
    # Can't use run_as_root here because the output takes time
    # and the usr might want to see it, especially if it fails.
    subprocess.call(['sudo', 'dhclient', '-v', iface])

def get_available_accesspoints(iface):
    aps = {}
    start_wpa_supplicant(iface)
    run_as_root(["wpa_cli", "scan"])
    out, err = run_as_root(["wpa_cli", "scan_results"])
    stdout_lines = out.split('\n')
    for line in stdout_lines:
        if not line or line.startswith('Selected') \
           or line.startswith('bssid /'):
            continue
        words = line.strip().split(maxsplit=4)

        # Get the ssid if it's not hidden, else use the MAC
        if len(words) == 4:
            ssid = '[%s]' % words[0]
        else:
            ssid = words[4]

        aps[ssid] = { 'MAC': words[0],
                      'flags': words[3],
                      'signal': int(words[2]),
                    }
    return aps

def get_known_networks():
    networks = {}
    out, err = run_as_root(["wpa_cli", "list_networks"])
    stdout_lines = out.split('\n')

    '''
Selected interface 'wlp2s0'
network id / ssid / bssid / flags
0       clink   any     [CURRENT]
    '''
    for line in stdout_lines:
        line = line.strip()
        if not line:
            continue
        words = line.split()
        if words[0].isdigit():
            networks[int(words[0])] = words[1]

    return networks

def get_wireless_ifaces():
    # For a list of all devices, ls /sys/class/net
    ifaces = []

    # Get a list of wireless interfaces.
    # iwconfig lists wireless interfaces on stdout, wired and lo on stderr.
    proc = subprocess.Popen(["iw", "dev"], shell=False,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_lines = proc.communicate()[0].decode().split('\n')
    for line in stdout_lines:
        line = line.strip()
        if line.startswith('Interface'):
            ifaces.append(line.split()[1])
            # could get MAC and ssid if appropriate

    return ifaces

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', "--known", dest="known",
                        action="store_true", help="List known networks")
    parser.add_argument('-a', "--available", dest="available",
                        action="store_true", help="Show available accesspoints")
    parser.add_argument('connect_to', nargs='?',
                        help="The essid or numeric specifier to connect to")

    args = parser.parse_args(sys.argv[1:])

    ifaces = get_wireless_ifaces()
    if not ifaces:
        print("No wireless interface, sorry")
        sys.exit(1)
    if len(ifaces) > 1:
        print("Multiple wireless interfaces:", ' '.join(get_wireless_ifaces()))
        print("Using", ifaces[0])
    iface = ifaces[0]

    if args.available:
        accesspoints = get_available_accesspoints(iface)

        aps = accesspoints.keys()

        known_nets = get_known_networks()
        known = []

        # Print the ones we have saved already:
        format = "%-20s %7s   %s"
        print(format % ("SSID", "Signal", "Known index"))
        print(format % ("----", "------", "-----------"))

        for i in sorted(known_nets):
            if known_nets[i] in aps:
                print(format % (known_nets[i],
                                accesspoints[known_nets[i]]['signal'], i))
                known.append(known_nets[i])

        # Print the ones we don't know:
        print()
        for ap in aps:
            if ap not in known:
                print(format % (ap, accesspoints[ap]['signal'], ''))
        sys.exit(0)

    if args.known:
        known_nets = get_known_networks()
        for i in sorted(known_nets.keys()):
            print('%3d: %s' % (i, known_nets[i]))
        sys.exit(0)

    # If no flags specified, then we should have one arg,
    # either a numeric specifier or an essid.
    if not args.connect_to:
        parser.print_help()
        sys.exit(1)

    connect_to = args.connect_to
    if verbose:
        print("Connecting to", connect_to)
    accesspoints = get_available_accesspoints(iface)
    aps = list(accesspoints.keys())
    known_nets = get_known_networks()
    known = [ known_nets[i] for i in known_nets ]
    known_index = None

    if connect_to not in aps:
        # But maybe it's a number for a known network?
        if connect_to.isdigit():
            known_index = int(connect_to)
            if known_index not in known_nets:
                print("No network %d known" % known_index)
                sys.exit(1)
            connect_to = known_nets[known_index]
            if connect_to not in aps:
                print("Network %d, '%s', not visible" % (known_index,
                                                         connect_to))
                sys.exit(1)
        else:
            print("'%s' isn't visible" % connect_to)
            sys.exit(1)

    # Now connect_to is an SSID that's known.
    if connect_to in known:
        if verbose:
            print("Great, we see", connect_to, "and we know it already")

        if known_index == None:
            for i in known_nets:
                if known_nets[i] == connect_to:
                    known_index = i
                    break
        if known_index == None:
            print("Internal error, lost track of SSID %s" % connect_to)

        if verbose:
            print("Enabling network", connect_to)
        run_as_root(["wpa_cli", "enable_network", str(known_index)])
        start_dhcp(iface)
        sys.exit(0)

    # New network, hasn't been stored yet. But it is seen.
    if verbose:
        print(connect_to, "must be a new network")
    thisap = accesspoints[connect_to]

    out, err = run_as_root(["wpa_cli", "add_network", connect_to])
    # The last (second) line of the output is the new network number.
    # But split('\n') gives a bogus empty final line.
    # To be safer, try iterating to find a line that's just a single number.
    lines = out.split('\n')
    netnum_str = None
    for line in lines:
        if not line:
            continue
        words = line.split()
        if len(words) == 1 and words[0].isdigit():
            netnum_str = words[0]
            break
    if not netnum_str:
        print("Unexpected output from wpa_cli add_network:")
        print(out)
        print("---")
        sys.exit(1)

    if verbose:
        print("new netnum:", netnum_str)

    run_as_root(["wpa_cli", "set_network", netnum_str, "ssid",
                 '"%s"' % connect_to])

    if 'WPA' in thisap['flags'] or 'PSK' in thisap['flags']:
        password = getpass.getpass("Password: ")

    out, err = run_as_root(["wpa_cli", "set_network", netnum_str,
                            "psk", '"%s"' % password])
    if 'FAIL' in out:
        print("Couldn't set password:\n")
        print(out)
        print(err)
        sys.exit(1)

    if verbose:
        print("Enabling network", netnum_str)
    out, err = run_as_root(["wpa_cli", "enable_network", connect_to])
    if 'FAIL' in out:
        print("Couldn't enable network")
        sys.exit(1)

    start_dhcp(iface)

    if verbose:
        print("Saving configuration")
    run_as_root(["wpa_cli", "save_config"])
    if verbose:
        print("Saved configuration")
    sys.exit(0)

