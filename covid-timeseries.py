#!/usr/bin/env python3

# Plot COVID data from the Corona Data Scraper.

import json
import argparse

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime

import sys, os


DATAFILEURL = 'https://coronadatascraper.com/timeseries-byLocation.json'

DATA_DIR = os.path.expanduser("~/Data/covid")


def fetch_data():
    datafile = os.path.join(DATA_DIR, 'timeseries-byLocation.json')

    # XXX Check last-mod date and update if needed
    if not os.path.exists(datafile):
        r = requests.get(DATAFILEURL)
        with open(datafile, 'wb') as datafd:
            datafd.write(r.content)
        print("Wrote", datafile)
    else:
        print(datafile, "was already cached")

    with open(datafile) as infp:
        return json.loads(infp.read())


covid_data = fetch_data()


def show_locations(matches):
    print("matches:", matches)
    for k in covid_data.keys():
        if matches:
            for m in matches:
                if m in k:
                    print(k)
                    break
        else:
            print(k)


def append_or_zero(lis, key, dic):
    if key in dic:
        lis.append(dic[key])
    else:
        lis.append(0)


def get_timeseries(location):
    dates = []
    cases = []
    newcases = []
    deaths = []
    recovered = []

    for d in covid_data[location]['dates']:
        dates.append(datetime.datetime.strptime(d, '%Y-%m-%d'))
        append_or_zero(cases, 'cases', covid_data[location]['dates'][d])
        if len(cases) >= 2:
            newcases.append(cases[-1] - cases[-2])
        else:
            newcases.append(0)
        append_or_zero(deaths, 'deaths', covid_data[location]['dates'][d])
        append_or_zero(recovered, 'recovered', covid_data[location]['dates'][d])

    # pprint(dates)
    # pprint(cases)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True, figsize=(10, 10))
    ax1.plot(dates, cases, label='Total cases')
    ax1.set_title('Total cases')
    ax2.plot(dates, newcases, color='green', label='New cases')
    ax2.set_title('New cases')
    ax3.plot(dates, deaths, color="red", label='Deaths')
    ax3.set_title('Deaths')

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
    plt.gcf().autofmt_xdate()
    plt.tight_layout(pad=2.0, w_pad=10.0, h_pad=3.0)

    plt.show()


# Location can be something like "NM, USA" or "Bernalillo County, NM, USA"
# Run with -L to see all locations, or -L 'pat' to show all locations
# that include a pattern.

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Do some stuff")
    parser.add_argument('-L', "--show-locations", dest="show_locations",
                        default=False, action="store_true",
                        help="Show all available locations")
    parser.add_argument('locations', nargs='*',
                        help="Locations to show")
    args = parser.parse_args(sys.argv[1:])
    print("args:", args)
    print("locations:", args.locations)

    if args.show_locations:
        show_locations(args.locations)
        sys.exit(0)

    get_timeseries(args.locations[0])


