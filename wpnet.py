#!/usr/bin/env python3

# A wrapper script to make it easier to use wpa_cli to connect.
# https://wiki.archlinux.org/index.php/WPA_supplicant#Connecting_with_wpa_cli
# was very helpful.
# Copyright 2018 by Akkana Peck: share and enjoy under the GPLv2 or later.

import subprocess
import os, sys
import argparse
import getpass
import urllib.request
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

def show_browser_if_redirect():
    """Try to fetch a test URL. If we're redirected to some other URL
       (probably a stupid login page), pop up a browser.
    """

    # Alas, there's no universal page everyone can use.
    # So make one on your own website, or find a trusted page,
    # and put that URL in ~/.config/netscheme/testurl
    testurl = None
    testurlfile = os.path.expanduser("~/.config/netscheme/testurl")
    if os.path.exists(testurlfile):
        with open(testurlfile) as tufile:
            testurl = tufile.read().strip()
        with open(testurlfile + ".out") as tufile:
            content_from_file = tufile.read()
    if not testurl:
        print("No test URL set; not checking for redirects")
        return

    content_from_web = ''
    print("Trying to fetch test URL", testurl)

    try:
        response = urllib.request.urlopen(testurl, timeout=100)

        # Were we redirected? In theory response.geturl() will tell us that,
        # but in practice, it doesn't, so we have to fetch the content
        # of a page and compare it to the expected value.
        content_from_web = response.read().decode('utf-8')

    # Lots of ways this can fail.
    # e.g. ValueError, "unknown url type"
    # or BadStatusLine: ''
    except Exception as e:
        print("Couldn't fetch test URL %s: probably redirected." % testurl, e)
        content_from_web = ''

    if content_from_web == content_from_file:
        print("Looks like we're really connected -- no redirect")
        return

    print("Couldn't make a test connection -- probably redirected.")

    # Don't want to run the browser as root, so de-escalate privilege.
    # os.getuid(), os.geteuid() and psutil.uids() are all zero under sudo,
    # but sudo helpfully leaves us an env variable we can use.
    orig_uid = os.getenv("SUDO_UID")
    if orig_uid:
        print("De-escalating back to UID", orig_uid)
        orig_uid = int(orig_uid)
        os.setuid(orig_uid)

    print("Calling quickbrowse", testurl)
    try:
        subprocess.call(["quickbrowse", testurl])
    except Exception as e:
        print("Problem starting a browser", e)
        raise e


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
        format = "%-20s %7s %4s  %s"
        print(format % ("SSID", "Signal", "#", "Encryption"))
        print(format % ("----", "------", "--", "----------"))

        for i in sorted(known_nets):
            if known_nets[i] in aps:
                print(format % (known_nets[i],
                                accesspoints[known_nets[i]]['signal'],
                                i,
                                accesspoints[known_nets[i]]['flags']))
                known.append(known_nets[i])

        '''
Sample flags:
SSID                  Signal    #  Encryption
----                  ------   --  ----------

LAC-Wireless             -86       [WPA2-EAP-CCMP][ESS]
Historical               -84       [WPA-PSK-TKIP][WPA2-PSK-CCMP+TKIP][ESS]
LAC PUBLIC               -85       [ESS]
Public-LAC               -90       [ESS]
NMC-Main                 -79       [WPA2-PSK-CCMP][ESS]

<iridum>- sudo wpa_cli scan_results                                           ~
Selected interface 'wlp2s0'
bssid / frequency / signal level / flags / ssid
58:bf:ea:92:ba:c0       2437    -48     [WPA2-EAP-CCMP][ESS]    LAC-Wireless
24:01:c7:3a:90:a0       2462    -73     [WPA2-EAP-CCMP][ESS]    LAC-Wireless
24:01:c7:3a:a9:f0       2412    -75     [WPA2-EAP-CCMP][ESS]    LAC-Wireless
6c:70:9f:de:4d:7c       2462    -84     [WPA-PSK-TKIP][WPA2-PSK-CCMP+TKIP][ESS]Historical
58:bf:ea:92:ba:c2       2437    -56     [ESS]   LAC PUBLIC
24:01:c7:3a:91:b0       2462    -64     [ESS]   Public-LAC
24:01:c7:3a:a2:80       2412    -65     [ESS]   Public-LAC
24:01:c7:3a:90:a2       2462    -70     [ESS]   LAC PUBLIC
24:01:c7:3a:a4:60       2462    -74     [ESS]   Public-LAC
24:01:c7:3a:a9:f2       2412    -76     [ESS]   LAC PUBLIC
6c:99:89:0d:43:80       2412    -84     [ESS]   Public-LAC
24:01:c7:3a:a4:52       2437    -88     [ESS]   LAC PUBLIC
24:01:c7:3a:a4:50       2437    -87     [WPA2-EAP-CCMP][ESS]    LAC-Wireless
64:ae:0c:1e:fd:32       2412    -87     [ESS]   LAC PUBLIC
24:01:c7:3a:4c:40       2462    -87     [WPA2-EAP-CCMP][ESS]    LAC-Wireless
24:01:c7:3a:81:d0       2462    -87     [ESS]   Public-LAC
24:01:c7:3a:a1:90       2437    -87     [ESS]   Public-LAC
24:01:c7:3a:a2:10       2412    -92     [WPA2-EAP-CCMP][ESS]    LAC-Wireless
50:60:28:28:aa:21       2412    -83     [WPA2-PSK-CCMP][ESS]    NMC-Main
24:01:c7:3a:a2:92       2462    -94     [ESS]   LAC PUBLIC
24:01:c7:3a:4c:42       2462    -88     [ESS]   LAC PUBLIC
64:ae:0c:1e:fd:30       2412    -89     [WPA2-EAP-CCMP][ESS]    LAC-Wireless
24:01:c7:3a:a2:90       2462    -90     [WPA2-EAP-CCMP][ESS]    LAC-Wireless
50:60:28:28:aa:20       2412    -82     [WPA2-PSK-CCMP][ESS]    NMC-Guest

Selected interface 'wlp2s0'


https://askubuntu.com/questions/541704/how-can-one-use-wpa-cli-to-connect-to-a-wpa-network-without-a-password

> scan
OK
CTRL-EVENT-SCAN-RESULTS 
> scan_results 
bssid / frequency / signal level / flags / ssid
f8:d1:11:23:c2:2f       2412    76      [ESS]   BAYINET
f8:d1:11:23:c1:e9       2412    47      [ESS]   BAYINET
> add_network
0
> set_network 0 ssid "Public-LAC"
OK
> set_network 0 key_mgmt NONE
OK
> enable_network 0
OK
CTRL-EVENT-SCAN-RESULTS
Trying to associate with f8:d1:11:23:c2:2f (SSID='BAYINET' freq=2412 MHz)
Association request to the driver failed
Associated with f8:d1:11:23:c2:2f
CTRL-EVENT-CONNECTED - Connection to f8:d1:11:23:c2:2f completed (auth) [id=1 id_str=]
> quit

'''

        # Print the ones we don't know:
        print()
        for ap in aps:
            if ap not in known:
                print(format % (ap,
                                accesspoints[ap]['signal'],
                                '',
                                accesspoints[ap]['flags']))
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
        show_browser_if_redirect()
        sys.exit(0)

    # New network, hasn't been stored yet. But it is seen.
    if verbose:
        print(connect_to, "must be a new network")
    thisap = accesspoints[connect_to]

    out, err = run_as_root(["wpa_cli", "add_network"])
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

    def check_fail(out, err, errmsg=None):
        if 'FAIL' in out or 'FAIL' in err:
            if errmsg:
                print("Error:", errmsg)
            print("==== FAIL: out")
            print(out)
            print("==== FAIL: err")
            print(err)
            sys.exit(1)

    out, err = run_as_root(["wpa_cli", "set_network", netnum_str, "ssid",
                 '"%s"' % connect_to])
    check_fail(out, err, "Set network")

    if 'WPA' in thisap['flags'] or 'PSK' in thisap['flags']:
        password = getpass.getpass("Password: ")

        out, err = run_as_root(["wpa_cli", "set_network", netnum_str,
                                "psk", '"%s"' % password])
        check_fail(out, err, "Set password")
    else:
        print("Trying to connect to %s with no password" % connect_to)
        out, err = run_as_root(["wpa_cli", "set_network", netnum_str,
                                "key_mgmt", "NONE"])
        check_fail(out, err, "Set key management")

    if verbose:
        print("Enabling network", netnum_str)
    out, err = run_as_root(["wpa_cli", "enable_network", connect_to])
    check_fail(out, err, "Enable network")

    start_dhcp(iface)

    # XXX It starts dhcp, then jumps straight to checking for redirect.
    # I never see "Saving configuration" and it never saves.
    # Why?
    # Possibly because while testing, the running wpa_supplicant
    # saw the ssid as known so we called show_browser_if_redirect()
    # from the known clause instead of from here.
    # Hopefully next time I get to test, that won't happen.
    if not verbose:
        print("Somehow verbose got set to False!")
        verbose = True
    if verbose:
        print("Saving configuration")
    out, err = run_as_root(["wpa_cli", "save_config"])
    check_fail("Save configuration")
    if verbose:
        print("Saved configuration")

    show_browser_if_redirect()

    sys.exit(0)

