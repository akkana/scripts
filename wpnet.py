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

verbose=False

'''
To run this as a normal user, not under sudo:
edit /etc/wpa_supplicant/wpa_supplicant.conf
and add a line like:
ctrl_interface_group=adm
using whatever group you think should have network permissions.

Commands this script runs:

** Get the wireless interface:
iw dev

** Start the daemon:
wpa_supplicant -B -i $iface -c /etc/wpa_supplicant/wpa_supplicant.conf

** List known networks:
wpa_cli list_networks

** List available networks:
wpa_cli scan
wpa_cli scan_results

** Define a new SSID:
wpa_cli add_network
  (prints new $ID. Then:)
NOT : wpa_cli set_network $ID

** Connect to a new open SSID:
wpa_cli set_network $ID ssid $SSID key_mgmt NONE
** Connect to a new WPA SSID:
wpa_cli set_network $ID ssid $SSID psk $PASSWORD

wpa_cli enable_network $ID
wpa_cli save_config


WORKED:

  wpa_supplicant -B -i wlp2s0  -c /etc/wpa_supplicant/wpa_supplicant.conf
  wpa_cli list_networks
  wpa_cli scan
  wpa_cli scan_results
  wpa_cli add_network
  wpa_cli set_network 1    (this gave an error, I think)
  wpa_cli set_network 1 ssid '"LAC-Public Library"'
  wpa_cli set_network 1 key_mgmt NONE
     (idiot bash lost this command, probably enable?)
  wpa_cli save_config
  dhclient -v wlp2s0
'''

def run_as_root(cmdargs):
    '''Run cmdargs inside sudo, unless we're already root.
       return (stdout, stderr) as strings.
    '''
    if os.getpid() != 0:
        cmdargs = ["sudo"] + cmdargs

    if verbose:
        print("\n** Run:", ' '.join(cmdargs))
    proc = subprocess.Popen(cmdargs, shell=False,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # proc.communicate() returns bytes, so change them to strings:
    return ( b.decode() for b in proc.communicate() )

def run_cmd(cmdargs):
    '''Run and return (stdout, stderr) as strings.
    '''
    if verbose:
        print("\n** Run:", ' '.join(cmdargs))
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
    # Can't use run_cmd here because the output takes time
    # and the usr might want to see it, especially if it fails.
    return subprocess.call(['sudo', 'dhclient', '-v', iface])

def get_available_accesspoints(iface):
    aps = {}
    start_wpa_supplicant(iface)
    run_cmd(["wpa_cli", "scan"])
    out, err = run_cmd(["wpa_cli", "scan_results"])
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

def get_current():
    '''
<iridum>- sudo wpa_cli list_networks                          ~/src/billtracker
Selected interface 'wlp2s0'
network id / ssid / bssid / flags
0       clink   any
1       LAC-Public Library      any     [CURRENT]
2       CommunityLab    any     [DISABLED]
3       COAFreeWireless any
4       LAC-Public Library      any
'''
    pass

def get_known_networks():
    start_wpa_supplicant(iface)
    networks = {}
    out, err = run_cmd(["wpa_cli", "list_networks"])
    stdout_lines = out.split('\n')

    for line in stdout_lines:
        line = line.strip()
        if not line:
            continue
        words = line.split('\t')
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
    if verbose and not testurl:
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


def show_available_networks():
    accesspoints = get_available_accesspoints(iface)

    aps = accesspoints.keys()

    known_nets = get_known_networks()

    # Print the ones we have saved already:
    format = "%-20s %7s %4s  %s"
    print(format % ("SSID", "Signal", "#", "Encryption"))
    print(format % ("----", "------", "--", "----------"))

    known = []
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
6c:70:9f:de:4d:7c       2462    -84     [WPA-PSK-TKIP][WPA2-PSK-CCMP+TKIP][ESS]Historical
58:bf:ea:92:ba:c2       2437    -56     [ESS]   LAC PUBLIC
24:01:c7:3a:91:b0       2462    -64     [ESS]   Public-LAC

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

def connect_to(to_ap):
    if verbose:
        print("Connecting to", to_ap)
    accesspoints = get_available_accesspoints(iface)
    aps = list(accesspoints.keys())
    known_nets = get_known_networks()
    known = [ known_nets[i] for i in known_nets ]
    known_index = None

    if to_ap not in aps:
        # But maybe it's a number for a known network?
        if to_ap.isdigit():
            known_index = int(to_ap)
            if known_index not in known_nets:
                print("No network %d known" % known_index)
                sys.exit(1)
            to_ap = known_nets[known_index]
            if to_ap not in aps:
                print("Network %d, '%s', not visible" % (known_index,
                                                         to_ap))
                sys.exit(1)
        else:
            print("'%s' isn't visible" % to_ap)
            sys.exit(1)

    # Now to_ap is an SSID that's known.
    if to_ap in known:
        if verbose:
            print("Great, we see", to_ap, "and we know it already")

        if known_index == None:
            for i in known_nets:
                if known_nets[i] == to_ap:
                    known_index = i
                    break
        if known_index == None:
            print("Internal error, lost track of SSID %s" % to_ap)

        if verbose:
            print("Enabling network", to_ap)

        run_cmd(["wpa_cli", "enable_network", str(known_index)])

        if start_dhcp(iface):
            print("DHCP failed")

        else:
            show_browser_if_redirect()

        sys.exit(0)

    # New network, hasn't been stored yet. But it is seen.
    if verbose:
        print(to_ap, "must be a new network")
    thisap = accesspoints[to_ap]

    out, err = run_cmd(["wpa_cli", "add_network"])
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
        print("==== SUCCESS: out")
        print(out)
        print("==== SUCCESS: err")
        print(err)

    out, err = run_cmd(["wpa_cli", "set_network", netnum_str, "ssid",
                 '"%s"' % to_ap])
    check_fail(out, err, "Set network")

    if 'WPA' in thisap['flags'] or 'PSK' in thisap['flags']:
        password = getpass.getpass("Password: ")

        out, err = run_cmd(["wpa_cli", "set_network", netnum_str,
                                "psk", '"%s"' % password])
        check_fail(out, err, "Set password")
    else:
        if verbose:
            print("Trying to connect to %s with no password" % to_ap)
        out, err = run_cmd(["wpa_cli", "set_network", netnum_str,
                                "key_mgmt", "NONE"])
        check_fail(out, err, "Set key management")

    if verbose:
        print("Waiting a little ...", end='')
    time.sleep(5)
    if verbose:
        print()

    if verbose:
        print("Enabling network", netnum_str)
    out, err = run_cmd(["wpa_cli", "enable_network", netnum_str])
    check_fail(out, err, "Enable network")

    if verbose:
        print("Waiting a little ...", end='')
    time.sleep(5)
    if verbose:
        print()

    if verbose:
        print("Saving configuration")
    out, err = run_cmd(["wpa_cli", "save_config"])
    check_fail(out, err, "Save configuration")
    if verbose:
        print(out, err, "Saved configuration")

    start_dhcp(iface)

    show_browser_if_redirect()

    sys.exit(0)



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
        show_available_networks()
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

    connect_to(args.connect_to)
