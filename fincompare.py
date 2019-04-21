#!/usr/bin/env python3

# Graph a bunch of financial assets (stocks or mutual funds)
# specified on the commandline by ticker symbols.
# (Downloads data from Yahoo finance.)
# Usage: fincompare.py fund fund ...

# You can also specify modules that do custom loading,
# in case you need to parse CSV or Excel files or any other local files.
# Just add those on the commandline, e.g. fincompare mybank.py IRCAX SCALX
# The name of the module must end in .py, e.g. mycsv.py
# It may include a full path to the file, e.g. ~/mydata/parse_my_data.py

# Your module must provide a function with this signature:
# plot_fund(color='b', marker='o')
# (of course you can choose your own defaults for color and marker).
# The function should return a triplet initial, start, end
# where initial is the initial value of the investment in dollars,
# and start and end are datetimes.

# You can't currently specify the date range unless you use a custom module.

# Copyright 2013 by Akkana Peck.
# Share and enjoy under the terms of the GPL v2 or later.

import sys, os
import time
import datetime
import math
import numpy as np

# http://blog.mafr.de/2012/03/11/time-series-data-with-matplotlib/
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# # from matplotlib.finance import quotes_historical_yahoo_ohlc as yahoo
# from mpl_finance import quotes_historical_yahoo_ohlc as yahoo
# matplotlib and mpl_finance can no longer read Yahoo data.
# They're supposed to be replaced by the pandas datareader,
# but unfortunately it can't read the data reliably either.
# Some possible alternatives are mentioned at
# http://www.financial-hacker.com/bye-yahoo-and-thank-you-for-the-fish/
# For now, alphavantage seems to be a good replacement.

#import csv
import json
import requests

outlog = ''
errlog = ''


# Separate reading the finance data into separate routines,
# since these web APIs change or disappear so often.
def read_finance_data(ticker, start_date, end_date):
    '''Return a dict,
       'dates': [list of datetime.date objects],
       'vals' : [list of floats]
    '''
    return read_finance_data_alphavantage(ticker, start_date, end_date)


def read_finance_data_alphavantage(ticker, start_date, end_date):
    cachedir = os.path.expanduser("~/.cache/fincompare")
    cachefile = os.path.join(cachedir, ticker + ".json")

    if os.path.exists(cachefile):
        print("Reading from cache file", cachefile)
        modtime = datetime.date.fromtimestamp(os.stat(cachefile).st_mtime)
        now = datetime.date.today()
        if (now - modtime) < datetime.timedelta(days=2):
            # Close enough, use the cache file.
            with open(cachefile) as fp:
                datadict = json.load(fp)
    else:
        key = os.getenv("ALPHAVANTAGE_KEY")
        if not key:
            raise RuntimeError("No Alphavantage key")

        # Adding &outputsize=compact gives only last 100 points;
        # &outputsize=full gives 20+ years historical data.
        outputsize = 'full'

        url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=%s&outputsize=%s&apikey=%s' % (ticker, outputsize, key)
        print("Requesting", url)

        r = requests.get(url)
        if r.status_code != 200:
            r.raise_for_status()
        with open(cachefile, 'w') as fp:
            print("Saving in cachefile", cachefile)
            fp.write(r.text)
        datadict = json.loads(r.text)

    if not datadict:
        return None

    # If you exceed the API limits (5/minute, 550/day) you still
    # get a response, but it's JSON with a long freetext error message.
    try:
        vals = datadict['Time Series (Daily)']
    except KeyError:
        if 'Note' not in datadict:
            raise RuntimeError("Unknown problem with query, saved in %s"
                               % cachefile)
        if 'API call frequency' in datadict['Note']:
            # Hit the limit.
            os.unlink(cachefile)
            print("Hit the API frequency limit. Try again in 1 minute...",
                  end='')
            sys.stdout.flush()
            for i in range(60):
                print(".", end='')
                sys.stdout.flush()
                time.sleep(1)
            print("Should work now.")
            sys.exit(0)

    retvals = { 'dates': [], 'vals': [] }
    d = start_date
    while d <= end_date:
        dstr = d.strftime('%Y-%m-%d')
        try:
            daydata = vals[dstr]
            adjclose = daydata["5. adjusted close"]
            retvals['dates'].append(d)
            retvals['vals'].append(float(adjclose))
        except Exception as e:
            # That day isn't there -- maybe a weekend or holiday
            # retvals.append(0.)
            # print(str(e))
            pass

        d += datetime.timedelta(days=1)

    return retvals


start = None
initial = None

#
# Read the list of funds to plot.
# If any of these ends in .py, assume it's a custom module;
# we'll try to load the module, which should include this function:
# plot_fund(color='b', marker='o')
#
imported_modules = {}

# Parse arguments:
if len(sys.argv) < 2 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
    print("Usage: %s [-iinitialval] [-sstarttime] fund [fund fund ...]" % os.path.basename(sys.argv[0]))
    print("No spaces between -i or -s and their values!")
    print("e.g. fincompare -i200000 -s2008-1-1 FMAGX FIRPX")
    sys.exit(1)
else:
    funds = []
    for f in sys.argv[1:]:
        if f.endswith('.py'):
            # First split off any pathname included,
            # since python isn't smart about importing from a pathname.
            fpath, ffile = os.path.split(f)
            if fpath:
                sys.path.append(fpath)

            try:
                imported_modules[f] = __import__(ffile[:-3])
            except Exception as e:
                print("Couldn't import", f)
                print(e)
        elif f.startswith('-s'):
            # Parse the start time:
            start = datetime.datetime.strptime(f[2:], '%Y-%m-%d').date()
        elif f.startswith('-i'):
            print("Trying initial from '%s'" % f[2:])
            initial = int(f[2:])
        elif f.startswith('-t'):
            timeout = int(f[2:])
        else:
            funds.append(f)

# Set up the plots:
fig = plt.figure(figsize=(12, 8))   # width, height in inches
ax1 = plt.subplot(111)

# Pick a different color and style for each plot.
# Sure would be nice if matplotlib could handle stuff like this for us.
# The impossible-to-find documentation for line styles is at:
# http://matplotlib.org/api/axes_api.html#matplotlib.axes.Axes.plot
# For colors, to use anything beyond the standard list, see
# http://matplotlib.org/api/colors_api.html
colors = [ 'b', 'r', 'g', 'c', 'y', 'k' ]
styles = [ '-', '--', ':', '-.' ]
markers = [ 'o', '*', 's', '^', 'p', '+', 'D', 'x', '|', 'h' ]

def pick_color(i):
    '''Pick a color that tries to be reasonably different
       from other colors so far picked.
    '''
    return colors[i % len(colors)] \
        + styles[int(i / len(colors))]
#        + markers[i%len(markers)]

def plot_funds(tickerlist, initial, start, end):
    '''Plot a fund by its ticker symbol,
       normalized to a given initial value.
    '''

    global outlog, errlog

    numdays = (end - start).days
    daysinyear = 365.0
    outlog += '%9s %9s %9s %9s\n' % ('Ticker', 'daily', 'CC', 'abs')

    # For testing, use something like
    # FUSVX = yahoo('FUSVX', datetime.datetime(2012, 10, 1),
    #                        datetime.datetime(2013, 4, 1),
    #                        asobject=True)
    for i, ticker in enumerate(tickerlist):
        try:
            fund_data = read_finance_data(ticker, start, end)
        except Exception as e:
            errlog += "Couldn't read %s\n" % ticker
            # raise e
            continue

        # Find the first nonzero value.
        # This may not be the first value, if the beginning of the
        # year was a weekend and thus a non-trading day.
        firstval = fund_data['vals'][0]
        lastval = fund_data['vals'][-1]

        # Calculate effective daily-compounded interest rate
        fixed_pct = lastval/firstval - 1.

        Rcc = daysinyear / numdays * \
            np.log(lastval / firstval)

        # Convert CC return to daily-compounded return:
        Rdaily = daysinyear * (math.exp(Rcc / daysinyear) - 1.)

        # Another attempt to compute the daily rate, but it's wrong.
        # Reff = daysinyear * (math.exp(math.log(fund_data['aclose'][-1]
        #                                        - fund_data['aclose'][0])
        #                               /numdays) - 1)

        outlog += "%9s %9.2f %9.2f %9.2f\n" % (ticker,
                                               Rdaily*100, Rcc*100,
                                               fixed_pct*100)

        # Normalize to the initial investment:
        fund_data['vals'] = [ initial * v/firstval for v in fund_data['vals'] ]

        np.set_printoptions(threshold=sys.maxsize)
        # print(ticker, "data:", fund_data['vals'])

        # and plot
        ax1.plot_date(x=fund_data['dates'], y=fund_data['vals'],
                      fmt=pick_color(i), label=ticker)
        # ax1.plot(fund_data, label=ticker)

for i, f in enumerate(imported_modules.keys()):
    # XXX This will overwrite any -i and -s.
    # Should instead normalize the value read to the -i value passed in.
    try:
        initial, start, end = imported_modules[f].plot_fund(color='k',
                                                marker=markers[i%len(markers)])
    except Exception as e:
        print("Couldn't plot", f)
        print(e)

if not initial:
    initial = 100000
if not start:
    start = datetime.date(2011, 1, 1)

end = datetime.date.today()

# Baseline at the initial investment:
plt.axhline(y=initial, color='k')

# This used to happen automatically, but then matplotlib started
# starting at 2000 rather than following the data. So better be sure:
ax1.set_xlim(start, end)

plot_funds(funds, initial, start, end)

print(outlog)
print("Errors:")
print(errlog)

ax1.set_ylabel("Value")
plt.grid(True)
plt.legend(loc='upper left')

# Rotate the X date labels. I wonder if there's any way to do this
# only for some subplots? Not that I'd really want to.
# In typical matplotlib style, it's a completely different syntax
# depending on whether you have one or multiple plots.
# http://stackoverflow.com/questions/8010549/subplots-with-dates-on-the-x-axis
# There is apparently no way to do this through the subplot.
# ax1.set_xticklabels(rotation=20)
plt.xticks(rotation=30)

# Exit on key q
def press(event):
    # print('press', event.key)
    sys.stdout.flush()
    if event.key == 'ctrl+q':
        sys.exit(0)
fig = plt.figure(1)
fig.canvas.mpl_connect('key_press_event', press)

# ax1.set_title("Investment options")

# This is intended for grouping muultiple plots, but it's also the only
# way I've found to get rid of all the extra blank space around the outsides
# of the plot and devote more space to the content itself.
plt.tight_layout()

plt.show()

