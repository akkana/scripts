#!/usr/bin/env python3

# Plot COVID data from the Corona Data Scraper.

import json
import argparse
import requests

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pprint import pprint

# import matplotlib.pyplot as plt
# import matplotlib.dates as mdates
import pygal

import sys, os


verbose = True

DATAFILEURL = 'https://coronadatascraper.com/timeseries-byLocation.json'

DATA_DIR = os.path.expanduser("~/Data/covid")


def fetch_data():
    datafile = os.path.join(DATA_DIR, 'timeseries-byLocation.json')
    needs_download = True

    # Check the data file's last-modified time, and update if needed.
    # The coronascraper updates at approximately 9pm PST, 5am UTC.
    # Use 6 UTC here to be safe.
    UTC_update_hour = 6
    try:
        # last mod time in UTC.
        filetime = datetime.utcfromtimestamp(os.stat(datafile).st_mtime)

        # Make a datetime for the last occurrence of 6 UTC.
        utcnow = datetime.utcnow()
        lastupdate = utcnow.replace(hour=UTC_update_hour, minute=0, second=0)
        if lastupdate > utcnow:
            lastupdate -= relativedelta(days=1)

        if lastupdate <= filetime:
            if verbose:
                print(datafile, "is cached and up to date")
            needs_download = False

    except FileNotFoundError:
        pass

    if needs_download:
        r = requests.get(DATAFILEURL)
        with open(datafile, 'wb') as datafd:
            datafd.write(r.content)
        if verbose:
            print("Fetched", datafile)

    with open(datafile) as infp:
        return json.loads(infp.read())


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


def get_allseries(covid_data, location):
    dates = []
    allseries = {
        'dates': [],
        'cases': [],
        'newcases': [],
        'deaths': [],
        'recovered': []
    }

    def append_or_zero(allseries, key, dic):
        if key in dic:
            allseries[key].append(dic[key])
        else:
            allseries[key].append(0)

    for d in covid_data[location]['dates']:
        dates.append(datetime.strptime(d, '%Y-%m-%d'))
        append_or_zero(allseries, 'cases',
                       covid_data[location]['dates'][d])
        if len(allseries['cases']) >= 2:
            allseries['newcases'].append(allseries['cases'][-1]
                                          - allseries['cases'][-2])
        else:
            allseries['newcases'].append(0)
        append_or_zero(allseries, 'deaths',
                       covid_data[location]['dates'][d])
        append_or_zero(allseries, 'recovered',
                       covid_data[location]['dates'][d])

    return dates, allseries


def plot_allseries_matplotlib(dates, allseries):

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True, figsize=(10, 10))
    ax1.plot(dates, allseries['cases'], label='Total cases')
    ax1.set_title('Total cases')
    ax2.plot(dates, allseries['newcases'], color='green', label='New cases')
    ax2.set_title('New cases')
    ax3.plot(dates, allseries['deaths'], color="red", label='Deaths')
    ax3.set_title('Deaths')

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
    plt.gcf().autofmt_xdate()
    plt.tight_layout(pad=2.0, w_pad=10.0, h_pad=3.0)

    plt.show()


def date_labels(start, end):
    """Generate labels for the 1st and 15th of each month"""
    labels = []

    # If starting before the 15th of the month, append the 15th first.
    if start.day < 15:
        start = start.replace(day=15)
        labels.append(start)

    # Set to the first of next month
    start = start.replace(day=1) + relativedelta(months=1)

    while start <= end:
        labels.append(start)
        ides = start.replace(day=15)
        if ides <= end:
            labels.append(ides)
        start += relativedelta(months=1)

    return labels


def plot_timeseries_pygal(dates, allseries, key, title):
    datetimeline = pygal.DateTimeLine(
        x_label_rotation=35, truncate_label=-1,
        title=f"COVID {title}", x_title=None, y_title=None,
        height=300,
        show_x_guides=True, show_y_guides=False,
        x_value_formatter=lambda dt: dt.strftime('%b %d'))

    # Don't add title (1st arg) here: it adds it as a legend on the left side
    # which then messes up the alignment of the three charts.
    datetimeline.add(None, list(zip(dates, allseries[key])))

    datetimeline.x_labels = date_labels(dates[0], dates[-1])

    outfile = f'{DATA_DIR}/covid-{key}.svg'

    # datetimeline.render_to_file(outfile)
    svg = datetimeline.render()

    # pygal loads a script from github and has no option to change that.
    # https://github.com/Kozea/pygal/issues/351
    # Load it locally instead
    evil_redirect = b'https://kozea.github.io/pygal.js/2.0.x/pygal-tooltips.min.js'
    svg = svg.replace(evil_redirect, b'pygal-tooltips.min.js')
    with open(outfile, 'wb') as outfp:
        outfp.write(svg)

    if verbose:
        print("Saved to", outfile)


def plot_allseries_pygal(dates, allseries, outfile):
    plot_timeseries_pygal(dates, allseries, 'cases', 'Cases')
    plot_timeseries_pygal(dates, allseries, 'newcases', 'New Cases')
    plot_timeseries_pygal(dates, allseries, 'deaths', 'Deaths')

    html_out = '''<!DOCTYPE html>
<html>
  <head>
    <title>COVID-19 Cases in New Mexico</title>
  </head>
  <body>
    <h1>COVID-19 Cases in New Mexico</h1>
    <figure>
        <embed type="image/svg+xml" src="covid-cases.svg" />
        <embed type="image/svg+xml" src="covid-newcases.svg" />
        <embed type="image/svg+xml" src="covid-deaths.svg" />
    </figure>
  </body>
</html>
'''
    if outfile:
        if not outfile.startswith('/'):
            outfile = os.path.join(DATA_DIR, outfile)
        with open(outfile, "w") as outfp:
            outfp.write(html_out)
            if verbose:
                print("Saved to", outfile)
    else:
        print('Content-type: text/html\n')
        print(html_out)


# Location can be something like "NM, USA" or "Bernalillo County, NM, USA"
# Run with -L to see all locations, or -L 'pat' to show all locations
# that include a pattern.

def main():
    global verbose, DATA_DIR

    # print("env keys:", os.environ.keys(), file=sys.stderr)

    # Run as a CGI?
    if 'REQUEST_URI' in os.environ:
        verbose = False
        DATA_DIR = os.path.dirname(os.getenv('SCRIPT_FILENAME'))

        covid_data = fetch_data()
        dates, allseries = get_allseries(covid_data, 'NM, USA')
        plot_allseries_pygal(dates, allseries, None)

    else:
        verbose = True
        parser = argparse.ArgumentParser(
            description="Plot COVID-19 data by location")
        parser.add_argument('-L', "--show-locations", dest="show_locations",
                            default=False, action="store_true",
                            help="Show all available locations")
        parser.add_argument('locations', nargs='*',
                            help="Locations to show")
        args = parser.parse_args(sys.argv[1:])

        if args.show_locations:
            show_locations(args.locations)
            sys.exit(0)

        covid_data = fetch_data()
        try:
            dates, allseries = get_allseries(covid_data, args.locations[0])
            # plot_allseries_matplotlib(dates, allseries)
            plot_allseries_pygal(dates, allseries, "covid.html")

        except IndexError:
            parser.print_help()
            sys.exit(1)


if __name__ == '__main__':
    main()

