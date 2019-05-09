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


class smart_time_locator(mticker.Locator):
    """A locator that audo-adjusts to the current data range,
       and provides both major (__call__()) and minor (minor())
       locators.
    """
    def __init__(self, minor=False):
        """
            If minor is True, calculate minor tick spacing instead of major.
        """
        self.minor = minor
        self.labeldict = {}


    def __call__(self):
        '''Called somehow, automagically, when a plot is drawn or rescaled.
           self.axis.get_data_interval() gives the data limits that should
           be drawn, as type numpy.float64.
           mdates.num2date() can turn them into datetime.
           Matplotlib expects __call__() to return a list of axis coordinates
           (ordinal floats).
        '''
        # dmin, dmax = self.datalim_to_dt()
        imin, imax = self.axis.get_data_interval()
        # translate to datetime.datetime
        dmin = mdates.num2date(imin)
        dmax = mdates.num2date(imax)
        print("dmin", dmin, ", dmax", dmax)
        # delta = mdates.relativedelta(dmax, dmin)
        delta = dmax - dmin
        if dmin > dmax:
            delta = -delta
        print("delta:", delta)

        # Defaults: XXX move these to fallback at end of this function
        # once all the other cases are fleshed out.
        def default_ticks(imin, imax):
            ticks = [imin, (imax-imin)/2, imax]
            labeldict = {}
            for t in ticks:
                labeldict[t] = mdates.num2date(t).strftime("%b %-d %H:%M")
            return ticks, labeldict

        # timedelta has only days, seconds, microseconds.
        # Let's not worry about subseconds.
        days = delta.days
        years = days / 365.2422
        print("days", days, "years", years)
        if years > 50:
            print("Argh, can't deal with 50+ years yet!")
            ticks, self.labeldict = default_ticks(imin, imax)
            return ticks

        if years >= 3:
            # label years
            print("Tick by years")
            ticks = []
            year = dmin.year
            while datetime.datetime(year, 1, 1) <= dmax:
                ticks.append(year)
                year += 1
            ticks.append(imax)
            # XXX Add formatting
            return ticks

        if days > 75:
            # go by months
            print("Tick by months")
            d = dmin.replace(day=1)
            ticks = []
            while d <= dmax:
                d_ord = mdates.date2num(d)
                ticks.append(d_ord)
                if not self.minor:
                    if d.month == 1:
                        self.labeldict[d_ord] = d.strftime("%Y %b %-d")
                    else:
                        self.labeldict[d_ord] = d.strftime("%b %-d")
                d = nextmonth(d)

            return ticks

        if days > 7:
            # By days
            print("Tick by days")
            d = dmin.replace(hour=0, minute=0)
            daydelta = datetime.timedelta(days=1)
            ticks = []
            while d <= dmax:
                d_ord = mdates.date2num(d)
                if self.minor or days < 15 or d.day % 5 == 0 \
                   or d.day == 1 or d == dmin:
                    ticks.append(d_ord)
                    if not self.minor:
                        self.labeldict[d_ord] = d.strftime("%b %-d")
                d += daydelta

            return ticks

        if days > 3:
            # By half-days (12 hours)
            print("Tick by half-days")
            d = dmin.replace(hour=0, minute=0)
            if self.minor:
                daydelta = datetime.timedelta(hours=1)
            else:
                daydelta = datetime.timedelta(hours=12)
            ticks = []
            while d <= dmax:
                d_ord = mdates.date2num(d)
                ticks.append(d_ord)
                if not self.minor:
                    if d.hour == 0:
                        self.labeldict[d_ord] = d.strftime("%b %-d %H:%M")
                    else:
                        self.labeldict[d_ord] = d.strftime("%H:%M")
                d += daydelta

            return ticks

        seconds = delta.total_seconds()
        hours = seconds / 3600
        minutes = hours / 60

        if hours > 5:
            # By hours
            print("Tick by hours")
            d = dmin.replace(hour=0, minute=0)
            hourdelta = datetime.timedelta(hours=1)
            ticks = []
            while d <= dmax:
                d_ord = mdates.date2num(d)
                ticks.append(d_ord)
                if not self.minor:
                    if d.hour == 0:
                        self.labeldict[d_ord] = d.strftime("%b %-d %H:%M")
                    else:
                        self.labeldict[d_ord] = d.strftime("%H:%M")
                d += hourdelta

            return ticks

        print("I'm confused!")
        ticks, self.labeldict = default_ticks(imin, imax)
        return ticks

    def formatter(self, time_ord, pos=None):
        '''Formatter to go with the locator.
           The locator remembers a dictionary mapping the time ordinals
           for each tick to a string, and this function just passes
           back the saved string.
           As far as I can tell, this will be called for every tick the
           locator specifies.
        '''
        # Major tick labels are a royal pain in the butt.
        # smart_time_locator can calculate all the labels at the same time
        # it calculates the ticks; but then there's no way to pass that
        # list back. ax.set_xticklabels() has to be called too early (e.g. here)
        # and isn't called again later after the locator has been called.
        # There's no way to control when the locator is called, or to set
        # a callback to happen after the locator has done its work and
        # passed back the tick labels.
        # The locator can remember the labels, but then there's no way
        # for it to pass them all back at once.
        # The only way I've found is a FncFormatter

        # Empirically, pos is the X position (in some unkmnown coordinates)
        # when setting up axis tics. It's zero when moving the mouse around
        # interactively. So we can use pos t tell the difference
        # between locating and labeling, though this is undocumented
        # and may change at some point.
        # print("daytime_formatter:", d, type(d))

        if not self.labeldict:
            return 'xxx'

        try:
            return self.labeldict[time_ord]
        except KeyError:
            return 'KeyError'


def smart_times_on_xaxis(ax):
    '''Call this function, passing in the Axis object,
       to get Major and minor formatter/locators for labeling any plot
       with smartly auto-scaled dates.
    '''

    # Is there a way to specify this on the axis, rather than globally?
    plt.xticks(rotation=45, ha="right")

    # Figure out the spacing for major labels (major_formatter),
    # minor labels (minor_formatter) and tics locators).

    # What's the date range shown on the plot?
    ordlimits = ax.get_xlim()
    datelimits = [ datetime.datetime.fromordinal(int(x))
                   for x in ordlimits ]
    daterange = datelimits[1] - datelimits[0]

    # How many pixels does this range represent?
    pixelrange = ax.transData.transform((ordlimits[1], 0.))[0] \
        - ax.transData.transform((ordlimits[0], 0.))[0]
    print(daterange, "spans", pixelrange, "pixels")

    # Major ticks:
    majorloc = smart_time_locator()
    ax.xaxis.set_major_locator(majorloc)

    # ax.xaxis.set_major_formatter(mticker.FuncFormatter(daytime_formatter))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(majorloc.formatter))
    # majorform = smart_time_formatter(majorloc)
    # ax.xaxis.set_major_formatter(mticker.FuncFormatter(majorform))
    # print("Labels:", '\n'.join(majorloc.labels), "(that's all)")
    # ax.set_xticklabels(mticker.FuncFormatter(majorloc.get_labels),
    #                    rotation = 45, ha="right")

    ax.tick_params(which='major', length=12, color='k')
    # Or set it separately for the major and ticks:
    # plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    # ax1.set_xticklabels(xticklabels, rotation = 45, ha="right")

    # Minor labels:
    ax.xaxis.set_minor_locator(smart_time_locator(minor=True))
    # No minor formatter: no labels for minor ticks.
    ax.tick_params(which='minor', length=3, color='r')

    # ax.grid(b=True, which='major', color='0.6', linestyle='-')
    # ax.grid(b=True, which='minor', color='.9', linestyle='-')


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
Two days by seconds: 2017-01-01T00:00 2017-01-02T00:00 sec

(ticks not yet working)

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

