#!/usr/bin/env python3

# Test various GeoIP solutions for the current external IP
# and collect the info in a log file,
# to check later how accurate or variable it is.

import requests
import re
from datetime import datetime
import os, sys

LOGFILE = os.path.expanduser("~/.config/geoip.log")

CHATTY = True

def duckduckgo():
    """Use the DuckDuckGo API to get the current external IP,
       and DDG's GeoIP estimate.
       Don't use this too much, or they'll cut you off and stop
       serving you any pages at all!
       Maybe this policy is explained in
       https://duckduckgo.com/api
       but I can't say since they won't serve me that page either!

       return ip, city, state, country, zipcode
    """
    try:
        r = requests.get('http://api.duckduckgo.com/?q=my+ip&format=json')
    except Exception as e:
        print("Exception from duckduckgo:", e)
        return None, None, None, None, None

    if r.status_code != 200:
        print("Response code from duckduckgo:", r.status_code)
        sys.exit(1)

    try:
        j = r.json()
    except Exception as e:
        print("Can't parse response as JSON")
        print(r.content)
        # raise(e)
        return None, None, None, None, None

    answerstring = j['Answer']

    # Parse out the relevant info
    ip = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', answerstring)[0]
    locstr = re.search('<a href=".+">(.+)</a>', answerstring).group(1)
    # 'Albuquerque, New Mexico, United States (87111)'
    city, state, country, zipcode = \
        re.search('(.+), (.+), (.+) \((\d{5})\)', locstr).groups()

    return ip, city, state, country, zipcode

def ip_api():
    """https://ip-api.com/docs/api:json

       return ip, city, state, country, zipcode
    """
    r = requests.get("http://ip-api.com/json/")
    if r.status_code != 200:
        print("Response code from ip-api:", r.status_code)
        return None, None, None, None, None

    try:
        j = r.json()
    except Exception as e:
        print("Can't parse response as JSON")
        print(r.content)
        # raise(e)
        return None, None, None, None, None

    if j["status"] != "success":
        print("unsuccessful response from ip_api:")
        from pprint import pprint
        pprint(j)
        return None, None, None, None, None

    return j["query"], j["city"], j["region"], j["country"], j["zip"]

def log_entry(ip, city, state, country, zipcode, service):
    if not os.path.exists(LOGFILE):
        headline = "city|state|country|zip|ip|date|service"
    else:
        headline = None
    with open(LOGFILE, "a") as logfp:
        if headline:
            print(headline, file=logfp)
        if CHATTY:
            print(service, "thinks we're in %s, %s, %s, %s"
                  % (city, state, country, zipcode))
        now = datetime.now()
        print('|'.join((city, state, country, zipcode, ip,
                        now.strftime("%Y-%m-%d"), service)),
              file=logfp)

if __name__ == '__main__':
    vals = ip_api()
    for service in ["ip_api", "duckduckgo"]:
        try:
            vals = globals()[service]()
            log_entry(*vals, service)
        except:
            print("Couldn't get geoip from", service)



