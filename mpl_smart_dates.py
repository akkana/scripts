#!/usr/bin/env python3

import matplotlib.dates as mdates
import matplotlib.ticker as mticker


def nextmonth(d):
    '''Beginning of the following month.
    '''
    month = d.month + 1
    year = d.year
    if month > 12:
        month = 1
        year += 1
    return d.replace(day=1, month=month, year=year)


def smart_time_ticks(imin, imax, minor=False):
    """Ticks that auto-adjusts to the current data range,
       and provides both major (__call__()) and minor (minor())
       locators.
    """
    '''Given the limits of the plot in float or numpy.float64 ordinals,
       return three lists:
         [ all major tick positions,
           all minor tick positions,
           all major tick labels ]
       , with the first two in float ordinals.
    '''
    # translate to datetime.datetime
    dmin = mdates.num2date(imin)
    dmax = mdates.num2date(imax)

    print("dmin", dmin, ", dmax", dmax)
    # delta = mdates.relativedelta(dmax, dmin)
    delta = dmax - dmin
    if dmin > dmax:
        delta = -delta
    print("delta:", delta)

    ticks = []
    ticklabels = []
    minor_ticks = []

    # Defaults: XXX move these to fallback at end of this function
    # once all the other cases are fleshed out.
    def default_ticks(imin, imax):
        ticks = [imin, (imax-imin)/2, imax]
        labeldict = {}
        for t in ticks:
            ticklabels.append(mdates.num2date(t).strftime("%b %-d %H:%M"))
        return ticks, minor_ticks, ticklabels

    # timedelta has only days, seconds, microseconds.
    # Let's not worry about subseconds.
    days = delta.days
    years = days / 365.2422
    print("days", days, "years", years)
    if years > 50:
        print("Argh, can't deal with that many years yet!")
        return default_ticks(imin, imax)

    if years >= 3:
        # label years
        print("Tick by years")
        ticks = []
        year = dmin.year
        while datetime.datetime(year, 1, 1) <= dmax:
            ticks.append(year)
            year += 1
        # XXX Add formatting, minor ticks
        return ticks, minor_ticks, ticklabels

    if days > 75:
        # go by months
        print("Tick by months")
        d = dmin.replace(day=1)
        while d <= dmax:
            d_ord = mdates.date2num(d)
            ticks.append(d_ord)
            if d.month == 1:
                ticklabels.append(d.strftime("%Y %b %-d"))
            else:
                ticklabels.append(d.strftime("%b %-d"))
            d = nextmonth(d)

        return ticks, minor_ticks, ticklabels

    if days > 7:
        # By days
        print("Tick by days")
        d = dmin.replace(hour=0, minute=0)
        daydelta = datetime.timedelta(days=1)
        while d <= dmax:
            d_ord = mdates.date2num(d)
            if days < 15 or d.day % 5 == 0 or d.day == 1 or d == dmin:
                ticks.append(d_ord)
                ticklabels.append(d.strftime("%b %-d"))
            else:
                minor_ticks.append(d_ord)
            d += daydelta

        return ticks, minor_ticks, ticklabels

    if days > 2:
        # By half-days (12 hours)
        print("Tick by half-days")
        d = dmin.replace(hour=0, minute=0)
        daydelta = datetime.timedelta(hours=12)
        while d <= dmax:
            d_ord = mdates.date2num(d)
            if d.hour == 0:
                ticks.append(d_ord)
                ticklabels.append(d.strftime("%b %-d %H:%M"))
            if d.hour == 12:
                minor_ticks.append(d_ord)
            d += daydelta

        print("ticks:", [ mdates.num2date(d) for d in ticks])
        print("minor_ticks:", [ mdates.num2date(d) for d in minor_ticks])
        return ticks, minor_ticks, ticklabels

    seconds = delta.total_seconds()
    hours = seconds / 3600
    minutes = hours / 60

    if hours > 5:
        # By hours
        print("Tick by hours")
        d = dmin.replace(hour=0, minute=0)
        hourdelta = datetime.timedelta(hours=1)
        while d <= dmax:
            d_ord = mdates.date2num(d)
            ticks.append(d_ord)
            if d.hour == 0:
                ticklabels.append(d.strftime("%b %-d %H:%M"))
            else:
                ticklabels.append(d.strftime("%H:%M"))
            d += hourdelta

        return ticks, minor_ticks, ticklabels

    print("I'm confused!")
    return default_ticks(imin, imax)


def smart_times_on_xaxis(ax):
    plt.xticks(rotation=45, ha="right")

    # What's the date range shown on the plot?
    # imin, imax = ax.get_xlim()
    # print("ax_xlim returned", mdates.num2date(imin), mdates.num2date(imax))
    # print("Interval:", [mdates.num2date(x) for x in ax.xaxis.get_data_interval()])
    imin, imax = ax.xaxis.get_data_interval()

    ticks, minor_ticks, ticklabels = smart_time_ticks(imin, imax)

    ax.set_xticks(ticks, minor=False)
    ax.set_xticklabels(ticklabels, minor=False)
    ax.tick_params(which='major', length=10, color='b')

    ax.set_xticks(minor_ticks, minor=True)
    # ax.set_xticklabels(minorloc.labellist, minor=True)
    ax.tick_params(which='minor', length=5, color='r')


if __name__ == '__main__':
    import datetime
    import matplotlib.pyplot as plt
    import sys, os

    def Usage():
        print('''Usage: %s start_date end_date interval
dates in format like 2017-01-01T00:00
interval may be day, hour, min, sec

(working)
Half month by day:   2017-01-01T00:00 2017-01-16T00:00 day
Two months by day:   2017-01-01T00:00 2017-03-01T00:00 day
One week by hour:    2017-01-01T00:00 2017-01-08T00:00 hour
Two years by day:    2017-01-01T00:00 2019-01-01T00:00 day
One day by seconds:  2017-01-01T00:00 2017-01-02T00:00 sec

(ticks not yet working)
Three days by minutes: 2017-01-01T00:00 2017-01-04T00:00 min

(neither test command parsing nor ticks working)
Three years by month:   2017-01-01T00:00 2020-01-01T00:00 month
Three years by week:    2017-01-01T00:00 2020-01-01T00:00 week
''' % (os.path.basename(sys.argv[0])))
        sys.exit(1)

    if len(sys.argv) < 4:
        Usage()

    start = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%dT%H:%M')
    end = datetime.datetime.strptime(sys.argv[2], '%Y-%m-%dT%H:%M')
    interval = sys.argv[3]
    print(start, end, interval)
    if interval == 'sec':
        delta = datetime.timedelta(seconds=1)
    elif interval == 'min':
        delta = datetime.timedelta(minutes=1)
    elif interval == 'hour':
        delta = datetime.timedelta(hours=1)
    elif interval == 'day':
        delta = datetime.timedelta(days=1)
    elif interval == 'month':
        delta = datetime.timedelta(months=1)
    else:
        print('Unknown interval "%s"' % interval)
        Usage()

    xvals = []
    d = start
    while d < end:
        xvals.append(d)
        d += delta

    fig = plt.figure(figsize=(10, 6))   # width, height in inches
    ax = fig.add_subplot(1, 1, 1)       # nrows, ncols, plotnum

    yvals = [ i % 5 - 1 for i in range(len(xvals)) ]

    ax.plot_date(x=xvals, y=yvals, ls='-', marker=None)

    smart_times_on_xaxis(ax)

    fig.tight_layout(pad=1.0, w_pad=10.0, h_pad=.5)
    plt.show()

