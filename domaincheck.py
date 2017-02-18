#!/usr/bin/env python

import sys
import whois
    # python-whois from pypi, not whois from pypi or python-whois from debian
import datetime
from dateutil.relativedelta import relativedelta

format="%25s %10s %8s"

if __name__ == '__main__':
    print(format % ("Domain", "Expires", ""))
    two_months_from_now = datetime.datetime.today() + relativedelta(months=2)
    two_months_from_now = two_months_from_now.date()
    for name in sys.argv[1:]:
        domain = whois.whois(name)
        if not domain["expiration_date"]:
            print "Can't get expiration date for", name
            continue
        elif hasattr(domain["expiration_date"], "__len__"):
            # Sometimes python-whois returns a list of dates,
            # for unknown reasons.
            # Check whether they're all the same.
            expdate = domain["expiration_date"][0].date()
            for e in domain["expiration_date"][1:]:
                if e.date() != expdate:
                    print "Yikes, %s != %s" % (str(e), str(expdate))
        else:
            expdate = domain["expiration_date"].date()
        # print "expdate:", expdate
        if expdate < two_months_from_now:
            alert = "***"
        else:
            alert = ""
        print(format % (name, expdate.strftime('%Y-%m-%d'), alert))
