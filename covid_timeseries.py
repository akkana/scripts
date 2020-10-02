#!/usr/bin/env python3

# Plot COVID data from the Covid Atlas, https://covidatlas.com/data
# (formerly Corona Data Scraper).

# import json
import csv
import argparse
import requests
import shutil

from datetime import datetime, date, timedelta, timezone
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as parsedate
from pprint import pprint

import pygal

import sys, os


verbose = True

DATAURL = "https://liproduction-reportsbucket-bhk8fnhv1s76.s3-us-west-1.amazonaws.com/v1/latest/"

DATA_DIR = os.path.expanduser("~/Data/covid")

LATEST     = "latest.csv"
TIMESERIES = "timeseries-tidy-small.csv"
LOCATIONS  = "locations.csv"

# Data before this UT hour will be considered to be the previous day's data.
# LATEST is supposedly "updated daily" but no time is specified.
# Based on one check, it has a 'Last-Modified': 'Tue, 22 Sep 2020 19:03:30 GMT'
# but will that be typical? Keep checking with
# curl -I https://liproduction-reportsbucket-bhk8fnhv1s76.s3-us-west-1.amazonaws.com/v1/latest/latest.csv
DATA_HOUR = 20

# Globals for the data:
covid_data = {}
dates = []


def find_locations(loclist, details=False):
    def matches_location(locname, locdict):
        if locname in locdict["locationID"]:
            return True
        if locname in locdict["name"]:
            return True
        return False

    locfile = os.path.join(DATA_DIR, LOCATIONS)
    if not os.path.exists(locfile):
        print("Downloading new location file")
        r = requests.get(DATAURL + LOCATIONS)
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


def append_dates_to(d):
    global dates
    if not dates:
        dates = [d]
        return
    while d > dates[-1]:
        dates.append(dates[-1] + timedelta(days=1))


def read_from_datafile(datafile, loclist):
    global covid_data, dates
    dates = []
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
                        covid_data[locID] = { }

                    # type is cases, deaths, recovered, growthFactor
                    ty = datadict["type"]

                    if ty not in covid_data[locID]:
                        covid_data[locID][ty] = []

                    # What's the index for this date?
                    d = datetime.strptime(datadict["date"],
                                          '%Y-%m-%d').date()
                    try:
                        dateindex = dates.index(d)
                    except:
                        dateindex = len(dates)
                        append_dates_to(d)

                    try:
                        val = int(datadict["value"])
                    except:
                        val = float(datadict["value"])
                    set_list_element(covid_data[locID][ty],
                                     dateindex, val)


def fetch_data(loclist):
    # I thought dicts didn't need to be declared global,
    # but apparently they do.
    global covid_data, dates

    datafile = os.path.join(DATA_DIR, TIMESERIES)

    need_timeseries = False
    need_latest = False

    try:
        read_from_datafile(datafile, loclist)
        last_date = dates[-1]
    except FileNotFoundError:
        last_date = date(1970, 1, 1)

    today = datetime.now(tz=timezone.utc).date()

    if last_date < today:
        print("Don't have any data for today. last_date is", last_date)
        # Is there a more recent "latest" file?
        h = requests.head(DATAURL + LATEST)
        url_date = parsedate(h.headers['last-modified']).date()
        print("url_date is", url_date)
        if url_date - last_date > timedelta(days=1):
            print("Last date is", last_date, "latest file is",
                  url_date, "-- need to download timeseries")

            print("Multiple days behind -- fetching new timeseries")

            r = requests.get(DATAURL + TIMESERIES)
            print("Fetched")

            newdatafile = datafile + "-NEW"
            with open(newdatafile, 'wb') as datafd:
                datafd.write(r.content)
            try:
                os.rename(datafile, datafile + ".bak")
            except:
                print("Couldn't rename")
                pass
            os.rename(newdatafile, datafile)
            print("Fetched", TIMESERIES)

        # elif last_date < url_date:
        else:
            print("Fetcing one day's data file")

            latestfile = os.path.join(DATA_DIR, 'latest.csv')
            r = requests.get(DATAURL + LATEST)
            with open(latestfile, 'wb') as latestfd:
                latestfd.write(r.content)
            print("Fetched", LATEST)

            # Append whatever's in the latest to the timeseries
            shutil.copy(datafile, datafile + ".bak")

            todaystr = datetime.now().strftime("%Y-%m-%d")
            with open(datafile, "a") as appendfp:
                with open(latestfile) as infp:
                    reader = csv.DictReader(infp)
                    for latestdict in reader:
                        for locdict in loclist:
                            if latestdict["locationID"] == locdict["locationID"]:
                                for key in ("cases", "deaths", "recovered"):
                                    val = latestdict[key]
                                    if val:
                                        print(f"{latestdict['locationID']},{url_date},{key},{val}",
                                              file=appendfp)
            print("Appended to", TIMESERIES)
    else:
        print("Data files are up to date")

    print("Reading from", datafile)
    read_from_datafile(datafile, loclist)

    # Whew, data supposedly read!
    # Generate newcases and percapita data for all locations
    for loc in loclist:
        locID = loc["locationID"]
        covid_data[locID]["newcases"] = []
        covid_data[locID]["percapita"] = []
        pop = int(loc["population"])
        for i, cases in enumerate(covid_data[locID]["cases"]):
            covid_data[locID]["percapita"].append(cases / pop)
            if i == 0:
                covid_data[locID]["newcases"].append(0)
            else:
                covid_data[locID]["newcases"].append(
                    covid_data[locID]["cases"][i] - \
                    covid_data[locID]["cases"][i-1])

    # Now covid_data should look something like:
    # { "iso1:us#iso2:us-nm#fips:35028": {
    #       "cases":  [ 0., 1., 3., ...],
    #       "deaths": [ 0., 0., 0., ...],
    # }
    # pprint(covid_data)
    print("Last date is", dates[-1])
    print("len dates:", len(dates))
    print("len cases:", len(covid_data[loclist[0]["locationID"]]["cases"]))


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


def plot_timeseries_pygal(key, loclist):
    locnames = ", ".join([l["county"] for l in loclist])
    tot = sum([covid_data[l['locationID']][key][-1] for l in loclist])
    # Integer or float?
    if int(tot) == tot:
        title = f"{tot} {key} in {locnames}"
    else:
        # XXX Is there a way to say "no more than 2 decimal places"
        # while leaving an option for less?
        title = f"{tot:.2f} {key} in {locnames}"

    datetimeline = pygal.DateTimeLine(
        x_label_rotation=35, truncate_label=-1,
        title=title,
        x_title=None, y_title=None,
        height=300,
        show_x_guides=True, show_y_guides=False,
        x_value_formatter=lambda dt: dt.strftime('%b %d'))

    # Don't add title (1st arg) here: it adds it as a legend on the left side
    # which then messes up the alignment of the three charts.
    for locdict in loclist:
        locID = locdict["locationID"]

        # The first argument to add() is the name of the plot,
        # which will be used for the legend.
        # But for a single county, the legend just takes away space
        # from the plot and doesn't add anything, so make the name
        # empty in that case.
        if len(loclist) > 1:
            locname = locdict["county"]
            if locname.endswith(" County"):
                locname = locname[:-7]
        else:
            locname = None
        datetimeline.add(locname, list(zip(dates, covid_data[locID][key])))

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


def plot_allseries_pygal(loclist, save_file=True):
    locnames = ", ".join([l["county"] for l in loclist])
    print("locnames:", locnames)
    plot_timeseries_pygal('cases', loclist)
    plot_timeseries_pygal('newcases', loclist)
    plot_timeseries_pygal('percapita', loclist)
    plot_timeseries_pygal('deaths', loclist)

    html_out = f'''<!DOCTYPE html>
<html>
  <head>
    <title>COVID-19 Cases in {locnames}</title>
  </head>
  <body>
    <h1>COVID-19 Cases in {locnames}</h1>
'''

    for locdict in loclist:
        html_out += f"""<b>{locdict["county"]:}</b>
{covid_data[locdict["locationID"]]["cases"][-1]} cases,
{covid_data[locdict["locationID"]]["newcases"][-1]} new cases,
{covid_data[locdict["locationID"]]["deaths"][-1]} deaths<br>"""

    html_out += f'''<figure>
        <embed type="image/svg+xml" src="covid-cases.svg" />
        <embed type="image/svg+xml" src="covid-newcases.svg" />
        <embed type="image/svg+xml" src="covid-percapita.svg" />
        <embed type="image/svg+xml" src="covid-deaths.svg" />
    </figure>

    <p>
    Source code: <a href="https://github.com/akkana/scripts/blob/master/covid_timeseries.py">covid_timeseries.py</a>.
    <p>
    Uses data from the <a href="https://covidatlas.com/data">Covid Atlas</a> project.
  </body>
</html>
'''

    if save_file:
        outfile = f'{DATA_DIR}/covid.html'
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
            plot_allseries_pygal(locs)

        except IndexError:
            parser.print_help()
            sys.exit(1)


if __name__ == '__main__':
    main()

