#!/usr/bin/env python

import sys

try:
    import whois
    # python-whois from pypi, not whois from pypi or python-whois from debian
    # https://bitbucket.org/richardpenman/pywhois
except:
    print("Couldn't import whois. Try: pip3 install python-whois")
    sys.exit(1)

import datetime
from dateutil.relativedelta import relativedelta

format="%25s   %10s %3s %s"

if __name__ == '__main__':
    domainlist = []
    for name in sys.argv[1:]:
        domain = whois.whois(name)
        if not domain["expiration_date"]:
            print("Can't get expiration date for %s" % name)
            continue
        elif hasattr(domain["expiration_date"], "__len__"):
            # Sometimes python-whois returns a list of dates,
            # for unknown reasons.
            # Check whether they're all the same.
            expdate = domain["expiration_date"][0].date()
            for e in domain["expiration_date"][1:]:
                if e.date() != expdate:
                    print("Yikes, %s != %s" % (str(e), str(expdate)))
        else:
            expdate = domain["expiration_date"].date()
        domainlist.append((name, expdate, domain.registrar))

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
