#!/usr/bin/env python3

# In many places, falling temperatures get a brief bump after sunset.
# But when, and how much, and for how long?
# This is an attempt to compare post-sunset temperature bumps
# among different locations, using whatever data is available.

# First, abstract fetching temperature as a function of time.
# Around Los Alamos, the LANL Weather Machine has the best data.
# In other places, I'm not sure what's best now that wunderground
# has closed off their API. Contributions and suggestions welcome.
# The function should have this signature:
# def get_day_temperatures(start_time, end_time)
# where times are datetime;
# it should return two lists, datetimes and floats.
#
# In most cases, it should be easiest to subclass DayWeatherFetcher
# to have a place to store details like URL, credentials, cache dirs, etc.

import datetime
import csv
import sys, os

from lanlweather import LANLWeather

class DayWeatherFetcher(object):

    def get_day_temperatures(day):
        '''
        @param day  The day for which to get temperatures

        @return       ([datetimes], [float temps])
        '''
        raise NotImplementedError

class LANLDayWeatherFetcher(DayWeatherFetcher):

    def __init__(self, tower, start, end):
        '''
           @param Tower  a namd, e.g. 'ta54',
           @param start  a datetime or a triple like [2017, 1, 1]
           @param end    a datetime or a triple like [2017, 1, 31]

           @return       ([datetimes], [float temps])
        '''

        self.lanlweather = LANLWeather(tower, start, end, ["temp0"])


    def get_day_temperatures(self, start_time, end_time):

        self.lanlweather.get_data()
        # Now have self.lanlweather.dates and self.lanlweather.data["temp0"]
        # lanlweather always gets full months at a time, so pare it down
        # if less than that was requested.

        dates = []
        vals = []

        for i, d in enumerate(self.lanlweather.dates):
            if d >= start_time and d <= end_time:
                dates.append(d)
                vals.append(self.lanlweather.data["temp0"][i])

        return dates, vals


class WatchweatherFetcher(DayWeatherFetcher):
    '''Watchweather keeps its data in CSV files named
       ~/.cache/watchserver/STATIONNAME-YYYY-MM-DD.csv.
    '''

    def __init__(self, cachedir, stationname):
        self.cachedir = cachedir
        self.stationname = stationname


    def get_day_temperatures(self, day):
        filename = os.path.join(self.cachedir,
                                'Home-%04d-%02d-%02d.csv' % (day.year,
                                                             day.month,
                                                             day.day))
        print("Filename:", filename)
        outdates = []
        outvals = []
        with open(filename) as csvfp:
            reader = csv.DictReader(csvfp)
            for row in reader:
                try:
                    if 'temperature' in row and 'time' in row:
                        outdates.append(datetime.datetime.strptime(row['time'],
                                                           '%Y-%m-%d %H:%M:%S'))
                        outvals.append(float(row['temperature']))

                except (KeyError, ValueError) as e:
                    print("Couldn't parse row:", row)
                    break

        return outdates, outvals


import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np


def plot_curves_by_date(dates, val_list, label_list, bumpdates=None):

    fig = plt.figure(figsize=(12, 8))   # width, height in inches

    for i, vals in enumerate(val_list):
        # ax = plt.subplot(2, 1, i+1)
        ax = fig.add_subplot(len(val_list), 1, i+1)

        ax.plot_date(x=dates, y=vals, label=label_list[i], ls='-', marker=None)

        ax.set_xlim(dates[0], dates[-1])

        ax.set_ylabel(label_list[i])

        # Matplotlib default date formatting is so useless, you basically
        # have to subclass it and write your own to get anything readable.
        def daytime_formatter(d, pos=None):
            '''Custom matplotlib formatter
               show the time of day except at midnight, when the date is shown.
            '''
            # Empirically, pos is the X position (in some unkmnown coordinates)
            # when setting up axis tics. However, later, when locating mouse
            # positions, pos is None. So we can use pos t tell the difference
            # between locating and labeling, though this is undocumented
            # and may change at some point.
            d = mdates.num2date(d)
            if pos == None:
                # pos==None is when you're moving the mouse interactively;
                # always want an indicator for that.
                return d.strftime("%b %d %H:%M")

            if d.hour == 0:
                return d.strftime("%m/%d %H:%M")
            return d.strftime("%H:%M")

        # Major ticks once a day:
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(daytime_formatter))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval = 4))
        ax.yaxis.set_major_locator(plt.MultipleLocator(10.0))
        ax.yaxis.set_minor_locator(plt.MultipleLocator(1.0))
        ax.tick_params(which='major', length=12, color='k')
        plt.xticks(rotation=45, ha="right")
        ax.grid(b=True, which='major', color='0.6', linestyle='-')
        ax.grid(b=True, which='minor', color='.9', linestyle='-')
        # Or set it separately for the major and ticks:
        # plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        # ax1.set_xticklabels(xticklabels, rotation = 45, ha="right")

        # Minor ticks every hour:
        ax.xaxis.set_minor_locator(mdates.HourLocator(interval = 1))
        ax.tick_params(which='minor', length=3, color='r')

        ax.legend(loc='upper right')

        # Are there any negative temperatures in vals?
        # If so, highlight the temp=0 axis so it's easier to see.
        for v in vals:
            if v < 0:
                ax.axhline(color='k', linewidth=.5)
                break

        if bumpdates:
            for bumpdate in bumpdates:
                ax.axvline(x=bumpdate, color='r', linewidth=1)
                #           label=str(bumpdate.time()))
                # axvline supposedly takes a lebel= parameter,
                # but in practice it doesn't do anything with it.
                # text() is another way, but it doesn't wrap to the plot
                # and if it overflows, then it messes up tight_layout
                # and we end up with the X axis labels being unreadable.
                # ax.text(x=bumpdate, y=80, s=bumpdate.strftime("%H:%M"),
                #         alpha=0.7, color='r')
                # annotate() gets around that.
                # xy, the "point to annotate", is meaningless since we're
                # annotating a vline, but it's required.
                ax.annotate(bumpdate.strftime("%H:%M"),
                            xy=(bumpdate, 50),
                            xytext=(bumpdate, 80),
                            clip_on=True)
                            # bbox={'facecolor':'red', 'clip_on':True})

    fig.tight_layout(pad=1.0, w_pad=10.0, h_pad=.5)

    plt.show()


def plot_raw_data(start_time, end_time):
    '''This is just a demo routine to show what the data looks like.'''

    # fetcher = WatchweatherFetcher(os.path.expanduser('~/.cache/watchserver'),
    #                               'Home')

    fetcher = LANLDayWeatherFetcher('ta54', start_time, end_time)

    dates, vals = fetcher.get_day_temperatures(start_time, end_time)

    vals = np.array(vals)
    dvals = np.gradient(vals)
    d2vals = np.gradient(dvals)

    # Draw lines where we found bumps
    bumpdays, bumphours = find_bump_times(dates, vals, dvals, None)
    # Convert to a list of datetimes:
    bumpdates = []
    for i, bumpday in enumerate(bumpdays):
        bumphour = int(bumphours[i])
        bumpmin = int((bumphours[i] - bumphour) * 60)
        bumpdates.append(datetime.datetime.combine(bumpday,
                                                   datetime.time(bumphour,
                                                                 bumpmin)))

    plot_curves_by_date(dates,
                        # [vals],
                        [vals, dvals],
                        # [vals, dvals, d2vals],
                        ["Temperatures", "Derivative", "2nd Derivative"],
                        bumpdates)


def find_bump_times(dates, vals, dvals, start_time=None):
    '''Find bump times for each day within the data passed in,
       subject to the given start time.
       start_time is a datetime.time; don't consider anything
       that happens earlier in the day than that.
       Return (list_of_dates, list_of_floats)
       where the floats are hours (e.g. 20.05 for a bump at 8:30 pm).
    '''
    if not start_time:
        start_time = datetime.time(17)

    # Make sure start_time is just a time, not a datetime
    elif hasattr(start_time, 'time'):
        start_time = start_time.time()

    dates_ret = []
    bump_hours = []

    # Loop over days:

    cur_day = dates[0].date()
    start_idx = None
    end_idx = None
    for i, d in enumerate(dates):

        # Find the slice for cur_day from start_time to midnight.
        day = d.date()
        # print(d, "(cur_day", cur_day, ")")
        if day < cur_day:    # shouldn't happen
            print(dates)
            raise RuntimeError("Dates must be out of order!")

        if day == cur_day:
            if start_idx == None:
                if d.time() >= start_time:
                    # print("Starting a day at", d)
                    start_idx = i
            continue

        if day > cur_day:
            end_idx = i
            # print("Ending a day at", dates[i])
            bump = find_bump_time(dates[start_idx:end_idx],
                                  vals[start_idx:end_idx],
                                  dvals[start_idx:end_idx],
                                  start_time)
            if bump:
                dates_ret.append(cur_day)
                bump_hours.append(bump)
            #     print("Found a bump on", cur_day)
            # else:
            #     print("No bump on", cur_day)
            cur_day = day

            # Starting a new day, so reset the indices.
            start_idx = None
            end_idx = None

    return dates_ret, bump_hours


def find_bump_time(dates, vals, dvals, start_time):
    '''Find bump time for a given day's data and a given start time
       (datetime.time)
       First find the time of the max temperature, and start an hour after that.
       Then look at the first derivative of the temperature;
       wait for it to go positive, then note when it goes negative again.
       Return the hour of the bump as a float,
       e.g. 20.05 for a bump at 8:30 pm;
       or None if no bump that day.
    '''
    # The position of the maximum temperature, measured from the end;
    # if there are multiple maxima, this will find the last one.
    maxtempidx = len(vals) - vals[::-1].argmax() - 1

    # Look for where the derivative goes positive, then record
    # the place where it goes negative again.
    started_climbing = False
    for i in range(maxtempidx, len(dvals)):
        if dates[i].time() < start_time:
            print(dates[i], "is before", start_time)
            continue

        v = dvals[i]
        if started_climbing and v < 0:
            # This is the local maximum of the first evening bump.
            print("Bump on", dates[i], "at", vals[i])
            return dates[i].hour + dates[i].minute / 60.
        if v > 0:
            started_climbing = True

    print("No bump on", dates[0])
    return None


def plot_evebumps(start_day, end_day):
    '''Find evebumps for each day, record the time, and plot them.
       start_day and end_day are datetimes or dates.
    '''

    # If start and end days are datetime, convert them to date:
    if hasattr(start_day, 'date'):
        start_day = start_day.date()
    if hasattr(end_day, 'date'):
        end_day = end_day.date()

    start_time = datetime.datetime.combine(start_day, datetime.time(0))
    end_time = datetime.datetime.combine(end_day, datetime.time(23, 59))
    fetcher = LANLDayWeatherFetcher('ta54', start_time, end_time)
    dates, vals = fetcher.get_day_temperatures(start_time, end_time)

    # Temperature values:
    vals = np.array(vals)
    # First derivative of temperature:
    dvals = np.gradient(vals)

    bumpdays, bumphours = find_bump_times(dates, vals, dvals)

    # print("bumpdays:", bumpdays)
    # print("bumphours:", bumphours)

    plot_curves_by_date(bumpdays, [ bumphours ], [ "Evebumps" ])


if __name__ == '__main__':

    if len(sys.argv) <= 1:
        plot_evebumps(datetime.datetime(2018, 6, 1),
                      datetime.datetime(2018, 6, 30))
        exit(0)

    start = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d')
    if len(sys.argv) > 2:
        end = datetime.datetime.strptime(sys.argv[2], '%Y-%m-%d')
    else:
        end = start

    plot_raw_data(start, end)
