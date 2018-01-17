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
import numpy

# http://blog.mafr.de/2012/03/11/time-series-data-with-matplotlib/
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# matplotlib and mpl_finance can no longer read Yahoo data.
# # from matplotlib.finance import quotes_historical_yahoo_ohlc as yahoo
# from mpl_finance import quotes_historical_yahoo_ohlc as yahoo
# They're supposed to be replaced by the pandas datareader,
# but unfortunately it can't read the data reliably either.
# Some possible alternatives are mentioned at
# http://www.financial-hacker.com/bye-yahoo-and-thank-you-for-the-fish/
import pandas_datareader as pdr
import pandas as pd

outlog = ''
errlog = ''

# Yahoo data will randomly and unpredictably fail, but waiting a while
# between fetches helps. Adjust the timeout as needed.
timeout = 7

# Separate reading the finance data into a separate routine,
# since these web APIs change and need to be adjusted so often.
first_time = True
def read_finance_data(ticker, start_date, end_date):
    global first_time
    if first_time:
        first_time = False
    else:
        print("(waiting %d secs) " % timeout, end='', file=sys.stderr)
        sys.stderr.flush()
        time.sleep(timeout)

    print("Fetching", ticker, "data", file=sys.stderr)
    fdata = pdr.DataReader(ticker,
                           data_source='yahoo',
                           start=start_date, end= end_date,
                           retry_count= 10)
    return fdata

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
if len(sys.argv) < 2:
    print("Usage: %s [-iinitialval] [-sstarttime] fund [fund fund ...]" % sys.argv[0])
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
            start = datetime.datetime.strptime(f[2:], '%Y-%m-%d')
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
            fund_data = read_finance_data(ticker, start, end)['Adj Close']
        except:
            errlog += "Couldn't read %s\n" % ticker
            continue

        # Guard against failures of quotes_historical_yahoo;
        # without this check you'll see more uncatchable RuntimeWarnings.
        if fund_data[0] == 0:
            print(ticker, ": First adjusted close is 0!")
            continue

        # Calculate effective daily-compounded interest rate
        fixed_pct = fund_data[-1]/fund_data[0] - 1.

        Rcc = daysinyear / numdays * \
            numpy.log(fund_data[-1] / fund_data[0])

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
        fund_data *= initial / fund_data[0]

        # and plot
        # ax1.plot_date(x=fund_data['date'], y=fund_data,
        #               fmt=pick_color(i), label=ticker)
        ax1.plot(fund_data, label=ticker)

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
    start = datetime.datetime(2011, 1, 1)

end = datetime.datetime.now()

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

ax1.set_title("Investment options")

# This is intended for grouping muultiple plots, but it's also the only
# way I've found to get rid of all the extra blank space around the outsides
# of the plot and devote more space to the content itself.
plt.tight_layout()

plt.show()

