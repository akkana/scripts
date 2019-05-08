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
        print("__call__ dmin", imin, ", dmax", imax)
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
        ticks = [imin, (imax-imin)/2, imax]
        self.labeldict = {}
        for t in ticks:
            self.labeldict[t] = mdates.num2date(t).strftime("%b %d %H:%M")

        # timedelta has only days, seconds, microseconds.
        # Let's not worry about subseconds.
        days = delta.days
        years = days / 365.2422
        if years > 50:
            print("Argh, can't deal with 50+ years yet!")
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
            return ticks

        if days > 75:
            # go by months
            # XXX
            print("Tick by months")
            d = dmin.replace(day=1)
            ticks = []
            while d <= dmax:
                ticks.append(d)
                print("Appending", d)
                d = nextmonth(d)
                print("next month:", d)
            ticks.append(imax)
            return ticks

        if days > 7:
            # By days
            print("Tick by days")
            d = dmin.replace(hour=0, minute=0)
            daydelta = datetime.timedelta(days=1)
            ticks = []
            while d <= dmax:
                d_ord = mdates.date2num(d)
                ticks.append(d_ord)
                self.labeldict[d_ord] = d.strftime("x %b %d %H:%M")
                d += daydelta
            ticks.append(imax)
            self.labeldict[imax] = dmax.strftime("x %b %d %H:%M")
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
                ticks.append(mdates.date2num(d))
                d += daydelta
            ticks.append(imax)

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
                ticks.append(d)
                d += hourdelta
            ticks.append(imax)
            return ticks

        print("I'm confused")
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


# class smart_time_formatter:
#     def __init__(self, locator):
#         # Save the smart locator, which hopefully will remember its
#         # current setting, axis limits etc.
#         self.locator = locator

#     def __call__(self, d, pos=None):
#         '''Custom matplotlib formatter:
#            show the time of day except at midnight, when the date is shown.
#            d is whatever units the locator returns; for dates, that has
#            to be ordinal floats, so use num2date() to turn into datetime.
#            As far as I can tell, this will be called for every tick the
#            locator specifies, and returns a string to be displayed.
#         '''
#         # Empirically, pos is the X position (in some unkmnown coordinates)
#         # when setting up axis tics. It's zero when moving the mouse around
#         # interactively. So we can use pos t tell the difference
#         # between locating and labeling, though this is undocumented
#         # and may change at some point.
#         # print("daytime_formatter:", d, type(d))
#         d = mdates.num2date(d)

#         if pos == None:
#             # pos==None is when you're moving the mouse interactively;
#             # always want an indicator for that.
#             return d.strftime("%b %d %H:%M")

#         if d.hour == 0:
#             return d.strftime("%m/%d %H:%M")
#         return d.strftime("%H:%M")


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

    def plot_vs_dates(xvals):
        yvals = [ i % 5 - 1 for i in range(len(xvals)) ]

        fig = plt.figure(figsize=(10, 6))   # width, height in inches
        ax = fig.add_subplot(1, 1, 1)   # nrows, ncols, plotnum

        ax.plot_date(x=xvals, y=yvals, ls='-', marker=None)

        smart_times_on_xaxis(ax)

        fig.tight_layout(pad=1.0, w_pad=10.0, h_pad=.5)

        plt.show()

    # One week, by hour
    # xvals = []
    # start = datetime.datetime(2017, 1, 1)
    # for i in range(7 * 24):
    #     xvals.append(start + datetime.timedelta(hours=i))
    # print("start", xvals[0].strftime('%Y-%m-%d %H:%M'),
    #       "end", xvals[-1].strftime('%Y-%m-%d %H:%M'))

    # Two months, by day
    xvals = []
    start = datetime.datetime(2017, 1, 1)
    for i in range(31):
        xvals.append(start + datetime.timedelta(hours=i*24))

    # # One year, by week
    # xvals = []
    # start = datetime.datetime(2017, 1, 1)
    # for i in range(52):
    #     xvals.append(start + datetime.timedelta(hours=i*24*7))

    # # One year, by day
    # xvals = []
    # start = datetime.datetime(2017, 1, 1)
    # for i in range(365):
    #     xvals.append(start + datetime.timedelta(hours=i*24))

    plot_vs_dates(xvals)
