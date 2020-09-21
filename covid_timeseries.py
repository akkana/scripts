#!/usr/bin/env python3

# Plot COVID data from the Covid Atlas, https://covidatlas.com/data
# (formerly Corona Data Scraper).

# import json
import csv
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

LATEST = "https://liproduction-reportsbucket-bhk8fnhv1s76.s3-us-west-1.amazonaws.com/v1/latest/"
TIMESERIES = "https://liproduction-reportsbucket-bhk8fnhv1s76.s3-us-west-1.amazonaws.com/v1/latest/timeseries-tidy-small.csv"
LOCATIONS = "https://liproduction-reportsbucket-bhk8fnhv1s76.s3-us-west-1.amazonaws.com/v1/latest/locations.csv"

DATA_DIR = os.path.expanduser("~/Data/covid")

# Globals for the data:
covid_data = {}
dates = []


def find_locations(loclist):
    def matches_location(locname, locdict):
        if locname in locdict["locationID"]:
            return True
        if locname in locdict["name"]:
            return True
        return False

    locfile = os.path.join(DATA_DIR, "locations.csv")
    if not os.path.exists(locfile):
        print("Downloading new location file")
        r = requests.get(DATAFILEURL)
        with open(locfile, 'wb') as locfd:
            locfd.write(r.content)

    locs = []

    with open(locfile) as fp:
        reader = csv.DictReader(fp)
        for locdict in reader:
            if not loclist:
                locs.append(locdict)
            else:
                for locname in loclist:
                    if matches_location(locname, locdict):
                        locs.append(locdict)

    return locs


def fetch_data(loclist):
    # I thought dicts didn't need to be declared global,
    # but apparently they do.
    global covid_data

    datafile = os.path.join(DATA_DIR, 'timeseries-tidy-small.csv')
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
        r = requests.get(TIMESERIES)
        with open(datafile, 'wb') as datafd:
            datafd.write(r.content)
        if verbose:
            print("Fetched", datafile)

    covid_data = {}
    with open(datafile) as infp:
        reader = csv.DictReader(infp)
        for datadict in reader:
            # Does this datadict line cover a location in the loclist?
            for locdict in loclist:
                if datadict["locationID"] == locdict["locationID"]:
                    # Yes, it's in the loc list. Add it.
                    locID = datadict["locationID"]
                    if locID not in covid_data:
                        covid_data[locID] = { "dates": [] }

                    # type is cases, deaths, recovered, growthFactor
                    ty = datadict["type"]

                    if ty not in covid_data[locID]:
                        covid_data[locID][ty] = []

                    # What's the index for this date?
                    d = datetime.strptime(datadict["date"], '%Y-%m-%d')
                    try:
                        dateindex = covid_data[locID]["dates"].index(d)
                    except:
                        dateindex = len(covid_data[locID]["dates"])
                        covid_data[locID]["dates"].append(d)

                    def set_list_element(lis, index, val):
                        """Set lis[index] = val,
                           filling in missing values with zeros as necessary.
                        """
                        try:
                            lis[index] = val
                            return
                        except IndexError:
                            while len(lis) < index:
                                lis.append(0)
                            lis.append(val)

                    val = float(datadict["value"])
                    set_list_element(covid_data[locID][ty], dateindex, val)

    # Now covid_data should look something like:
    # { "iso1:us#iso2:us-nm#fips:35028": {
    #       "dates":  [  "2020-01-22", "2020-01-23", ... ]
    #       "cases":  [ 0., 1., 3., ...],
    #       "deaths": [ 0., 0., 0., ...],
    # }
    # pprint(covid_data)


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


def plot_timeseries_pygal(key, title, locdict):
    locID = locdict["locationID"]
    locname = locdict["name"]
    dates = covid_data[locID]["dates"]

    datetimeline = pygal.DateTimeLine(
        x_label_rotation=35, truncate_label=-1,
        title=f"COVID {title}", x_title=None, y_title=None,
        height=300,
        show_x_guides=True, show_y_guides=False,
        x_value_formatter=lambda dt: dt.strftime('%b %d'))

    # Don't add title (1st arg) here: it adds it as a legend on the left side
    # which then messes up the alignment of the three charts.
    datetimeline.add(None, list(zip(dates, covid_data[locID][key])))

    datetimeline.x_labels = date_labels(dates[0], dates[-1])

    outfile = f'{DATA_DIR}/covid-{key}-{locname}.svg'

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


# def plot_allseries_pygal(dates, allseries, regiontitle, save_file):
def plot_allseries_pygal(locdict, save_file=True):
    plot_timeseries_pygal('cases', f'Total Cases in {locdict["name"]}', locdict)
    # plot_timeseries_pygal(dates, allseries, f'newcases', 'New Cases', region)
    plot_timeseries_pygal('deaths', f'Deaths in {locdict["name"]}', locdict)

    regiontitle = locdict["name"]
    region = regiontitle

    html_out = f'''<!DOCTYPE html>
<html>
  <head>
    <title>COVID-19 Cases in {regiontitle}</title>
  </head>
  <body>
    <h1>COVID-19 Cases in {regiontitle}</h1>
    <figure>
        <embed type="image/svg+xml" src="covid-cases-{region}.svg" />
        <embed type="image/svg+xml" src="covid-newcases-{region}.svg" />
        <embed type="image/svg+xml" src="covid-deaths-{region}.svg" />
    </figure>

    <p>
    Source code: <a href="https://github.com/akkana/scripts/blob/master/covid_timeseries.py">covid_timeseries.py</a>.
    <p>
    Uses data from the <a href="https://covidatlas.com/data">Corona Atlas</a> project.
  </body>
</html>
'''

    if save_file:
        outfile = f'{DATA_DIR}/covid-{region}.html'
        with open(outfile, "w") as outfp:
            outfp.write(html_out)
            if verbose:
                print("\nHTML file:", outfile)
    else:
        print('Content-type: text/html\n')
        print(html_out)


# Location can be something like "Los Alamos" or "fips:35028" or just 35028.
# To show all counties in a state, use "County, New Mexico"
# Run with -L to see all locations (long list!),
# or -L 'pat' to show all locations that match a pattern.

def main():
    global verbose, DATA_DIR

    # Run as a CGI?
    if 'REQUEST_URI' in os.environ:
        verbose = False
        DATA_DIR = os.path.dirname(os.getenv('SCRIPT_FILENAME'))

        covid_data = fetch_data()
        region = 'NM, USA'
        dates, allseries = get_allseries(covid_data, region)
        plot_allseries_pygal(dates, allseries, region, False)

    else:
        verbose = True
        parser = argparse.ArgumentParser(
            description="Plot COVID-19 data by location")
        parser.add_argument('-L', "--show-locations", dest="show_locations",
                            default=False, action="store_true",
                            help="Show all available locations")
        parser.add_argument('locations', nargs='+',
                            help="Locations to show")
        args = parser.parse_args(sys.argv[1:])

        locs = find_locations(args.locations)

        if args.show_locations:
            for loc in locs:
                print(loc["name"], loc["locationID"])
            sys.exit(0)

        fetch_data(locs)
        print("Fetched data")

        try:
            # dates, allseries = get_allseries(covid_data, args.locations[0])

            loc = locs[0]
            plot_allseries_pygal(loc)

        except IndexError:
            parser.print_help()
            sys.exit(1)


if __name__ == '__main__':
    main()

