#!/usr/bin/env python

import sys
import datetime

# http://blog.mafr.de/2012/03/11/time-series-data-with-matplotlib/
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.finance import quotes_historical_yahoo

#
# Read the list of funds to plot.
# If any of these ends in .py, assume it's a custom module;
# we'll try to load the module, which should include this function:
# plot_fund(color='b', marker='o')
#
if len(sys.argv) < 2 :
    funds = ['VFIAX', 'FUSVX', 'LDLAX', 'VSCGX', 'IRCAX', 'SCALX', 'SRCMX']
else :
    funds = []
    imported_modules = {}
    for f in sys.argv[1:] :
        if f.endswith('.py') :
            try :
                imported_modules[f] = __import__(f[:-3])
            except :
                print "Couldn't import", f
        else :
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
markers = [ 'o', '*', 's', '^', 'h', '+', 'D', 'x', '|' ]

def pick_color(i) :
    '''Pick a color that tries to be reasonably different
       from other colors so far picked.
    '''
    return colors[i % len(colors)] + styles[int(i / len(colors))]

def plot_funds(tickerlist, initial, start, end) :
    '''Plot a fund by its ticker symbol,
       normalized to a given initial value.
    '''
    # For testing, use something like
    # FUSVX = quotes_historical_yahoo('FUSVX', datetime.datetime(2012, 10, 1),
    #                                 datetime.datetime(2013, 4, 1),
    #                                 asobject=True)
    for i, ticker in enumerate(tickerlist) :
        fund_data = quotes_historical_yahoo(ticker, start, end,
                                            asobject=True)

        # Normalize to the initial investment:
        fund_data['aclose'] *= initial / fund_data['aclose'][0]

        # and plot
        ax1.plot_date(x=fund_data['date'], y=fund_data['aclose'],
                      fmt=pick_color(i), label=ticker)

initial = None
for i, f in enumerate(imported_modules.keys()) :
    try :
        initial, start, end = imported_modules[f].plot_fund(color='k',
                                                marker=markers[i%len(markers)])
    except :
        print "Couldn't plot", f

if not initial :
    initial = 100000
    start = datetime.datetime(2011, 1, 1)
    end = datetime.datetime.now()

# Baseline at the initial investment:
plt.axhline(y=initial, color='k')

plot_funds(funds, initial, start, end)

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
# fig = plt.figure(1)
plt.xticks(rotation=30)

ax1.set_title("Investment options")

# This is intended for grouping muultiple plots, but it's also the only
# way I've found to get rid of all the extra blank space around the outsides
# of the plot and devote more space to the content itself.
plt.tight_layout()

plt.show()

