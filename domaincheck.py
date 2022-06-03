#!/usr/bin/env python

# Display renewal dates for a list of domains given on the command line.
# Copyright 2021 by Akkana Peck; share and enjoy under the GPLv3 or later.

# There are quite a few Python whois packages, including at least two
# that are named "whois" for purposes of import.
# python-whois, from pypi, https://bitbucket.org/richardpenman/pywhois,
# tends to time out on at least half its queries; sometimes retrying
# helps, but even with multiple retries it will miss some domains.
# whois from apt install python3-whois apparently parses the
# output from /usr/bin/whois, and is slightly more reliable,
# but you'll still see timeouts.

from __future__ import print_function

import sys

try:
    import whois
    # python-whois from pypi, not whois from pypi or python-whois from debian
    # https://bitbucket.org/richardpenman/pywhois
except:
    print("""Couldn't import whois. Try:
    apt install python3-whois
or
    pip3 install python-whois
(Those are two different packages, but both are supported.
The one from pip tends to time out; the one from apt is more reliable.)
""")
    sys.exit(1)

import socket     # for the socket.timeout exception

import datetime
from dateutil.relativedelta import relativedelta

format="%25s   %10s %3s %s"


def get_domain(domainname):
    """Get info for a domain name, figuring out which whois module
       is installed.
        Return an object that includes:
          .expiration_date: which may be a datetime or a list of datetimes
          .registrar:       string
    """
    # Is it the apt version?
    if hasattr(whois, 'query'):
        return get_domain_apt_python3whois(domainname)
    return get_domain_pip_pythonwhois(domainname)


# whois is super unreliable, often timing out.
RETRIES = 6


def get_domain_apt_python3whois(domainname):
    """Get domain info using the whois from apt install python3-whois
    """
    for i in range(RETRIES):
        try:
            return whois.query(domainname)
        except:
            # Yuck, this whois module just raises a generic Exception.
            print("Problem on", domainname, "retrying ...",
                  file=sys.stderr)
    print("Giving up on %s after %d timeouts" % (domainname, RETRIES),
          file=sys.stderr)
    return None


def get_domain_pip_pythonwhois(domainname):
    """Get domain info using whois from pip install python-whois.
       This tends to time out a lot and needs a lot of retries.
    """
    for i in range(RETRIES):
        try:
            domain = whois.whois(name)
            return domain
        except socket.timeout:
            print("%s: timed out, retrying" % domainname, file=sys.stderr)
        except ConnectionResetError:
            print("%s: ConnectionResetError, retrying" % domainname,
                  file=sys.stderr)
        except whois.parser.PywhoisError:
            print("%s: No such domain" % domainname, file=sys.stderr)
            return None
        except Exception as e:
            print("%s: unexpected Exception on" % domainname, file=sys.stderr)
            print(e)
            print("Retrying...")
    print("Giving up on %s after %d timeouts" % (domainname, RETRIES),
          file=sys.stderr)
    return None


if __name__ == '__main__':
    domainlist = []
    for name in sys.argv[1:]:
        domain = get_domain(name)
        if not domain:
            print("Can't get info for %s" % name)
            continue
        if not domain.expiration_date:
            print("WARNING: Can't get expiration date for %s" % name)
            continue
        elif hasattr(domain.expiration_date, "__len__"):
            # Sometimes python-whois returns a list of two dates,
            # for undocumented reasons.
            # Typically they're one day apart, with the second date
            # being later, but that's probably not safe to count on.
            # Find the earliest date in the list.
            expdate = min(domain.expiration_date)
        else:
            expdate = domain.expiration_date

        if domain:
            domainlist.append((name, expdate.date(), domain.registrar))

    domainlist.sort(key = lambda a: a[1])

    two_months_from_now = datetime.datetime.today() + relativedelta(months=2)
    two_months_from_now = two_months_from_now.date()
    print(format % ("Domain", "Expires", "", "Registrar"))
    for d in domainlist:
        if d[1] < two_months_from_now:
            alert = "***"
        else:
            alert = ""
        print(format % (d[0], d[1].strftime('%Y-%m-%d'), alert, d[2]))
