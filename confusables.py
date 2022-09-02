#!/usr/bin/env python3

# Use the unicode.org "confusables" list to read or create
# strings using confusingly similar unicode characters.

import re
from collections import defaultdict
import json
import argparse
import sys, os


URL = "http://www.unicode.org/Public/security/latest/confusables.txt"

DATADIR = os.path.expanduser("~/Data/confusables")

linepat = "([0-9A-Fa-f]{4,8}).*;.*([0-9A-Fa-f]{4,8}).*;.*?# (.*) *#"

jsonfile = os.path.join(DATADIR, "confusetable.json")


def fetch_new_data():
    import requests
    r = requests.get(URL)
    confusedata = r.text

    with open(os.path.join(DATADIR, "confusables.txt"), 'w') as fp:
        fp.write(confusedata)

    confusetable = defaultdict(list)
    for line in confusedata.splitlines():
        if not line or line.startswith("#"):
            continue
        match = re.match(linepat, line)
        if not match:
            continue
        similarchar, commonchar, desc = match.groups()
        print("similarchar", similarchar, type(similarchar))
        similarchar = chr(int(similarchar, 16))
        commonchar = chr(int(commonchar, 16))
        confusetable[commonchar].append((similarchar, desc))

    # Write it as JSON
    with open(jsonfile, "w") as fp:
        json.dump(confusetable, fp)
        print("Wrote to", jsonfile)

    return confusetable


def read_json(filename):
    with open(filename) as jsonfp:
        confusetable = json.loads(jsonfp.read())
    return confusetable


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Show or create strings with deceptive Unicode characters")
    # parser.add_argument('-c', "--check", dest="check", default=False,
    #                     action="store_true", help="Help string")
    parser.add_argument('strings', nargs='?', help="Strings to analyze")
    args = parser.parse_args(sys.argv[1:])
    print(args)

    if not os.path.exists(jsonfile):
        fetch_new_data()

    with open(jsonfile) as jsonfp:
        confusetable = json.load(jsonfp)

    for s in args.strings:
        print(s, ":")
        for c in s:
            if c in confusetable:
                print("  ", c)
            else:
                for k in confusetable:
                    for pair in confusetable[k]:
                        if c == pair[0]:
                            print("  ", c, pair[1])

