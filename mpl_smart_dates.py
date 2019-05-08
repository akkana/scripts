#!/usr/bin/env python3

import matplotlib.dates as mdates
import matplotlib.ticker as mticker


def nearest_sensible_unit(td):
    '''Find the nearest whole/sensible unit to the timedelta passed in.
       return (years, weeks, months, days, hours, minutes)
       but only one of those quantities will be set; the rest will be 0.
    '''
    if td.days > 740:
        return (1, 0, 0, 0, 0, 0)
    if td.days > 60:
        return (0, 1, 0, 0, 0, 0)
    if td.days > 1:
        pass


def nextmonth(d):
    '''Beginning of the following month.
    '''
    month = d.month + 1
    year = d.year
    if month > 12:
        month = 1
        year += 1
    return d.replace(day=1, month=month, year=year)


class smart_date_locator(mticker.Locator):
    """A locator that audo-adjusts to the current data range,
       and provides both major (__call__()) and minor (minor())
       locators.
    """
    def __init__(self, minor=False):
        """
            If minor is True, calculate minor tick spacing instead of major.
        """
        self.minor = minor


    def __call__(self):
        '''Called somehow, automagically, when a plot is drawn or rescaled.
           self.axis.get_data_interval() gives the data limits that should
           be drawn, as type numpy.float64.
           mdates.num2date() can turn them into datetime.
           Matplotlib expects __call__() to return a list of axis coordinates
           (ordinal floats).
        '''
        print()
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
        print("delta", delta)

        # timedelta has only days, seconds, microseconds.
        # Let's not worry about subseconds.
        days = delta.days
        years = days / 365.2422
        if years > 50:
            print("Argh, can't deal with 50+ years yet!")
            return [imin, (imax-imin)/2, imax]

        if years >= 3:
            # label years
            print("labeling years")
            ret = []
            year = dmin.year
            while datetime.datetime(year, 1, 1) <= dmax:
                ret.append(year)
                year += 1
            ret.append(imax)
            return ret

        if days > 75:
            # go by months
            # XXX
            print("labeling months")
            d = dmin.replace(day=1)
            ret = []
            while d <= dmax:
                ret.append(d)
                print("Appending", d)
                d = nextmonth(d)
                print("next month:", d)
            print("Returning", ret)
            ret.append(imax)
            return ret

        if days > 7:
            # By days
            print("Labeling days")
            d = dmin.replace(hour=0, minute=0)
            daydelta = datetime.timedelta(days=1)
            ret = []
            while d <= dmax:
                ret.append(mdates.date2num(d))
                d += daydelta
            print("Returning", ret)
            ret.append(imax)
            return ret

        if days > 3:
            # By half-days (12 hours)
            print("Labeling half-days")
            d = dmin.replace(hour=0, minute=0)
            if self.minor:
                daydelta = datetime.timedelta(hours=1)
            else:
                daydelta = datetime.timedelta(hours=12)
            ret = []
            while d <= dmax:
                ret.append(mdates.date2num(d))
                d += daydelta
            print("Returning", ret)
            ret.append(imax)
            return ret

        seconds = delta.total_seconds()
        hours = seconds / 3600
        minutes = hours / 60

        if hours > 5:
            # By hours
            print("Labeling hours")
            d = dmin.replace(hour=0, minute=0)
            hourdelta = datetime.timedelta(hours=1)
            ret = []
            while d <= dmax:
                ret.append(d)
                d += hourdelta
            print("Returning", ret)
            ret.append(imax)
            return ret

        print("I'm confused")
        return [imin, (imax-imin)/2, imax]


    # The matplotlib ticker doc
    # https://matplotlib.org/api/ticker_api.html
    # says to override autoscale, but it evidently doesn't mean
    # there's actually a function by that name that should be defined.
    # Lord knows what it actually does mean since it doesn't give
    # any examples.
    #
    # def autoscale(self):
    #     """
    #     Set the view limits to include the data range.
    #     """
    #     dmin, dmax = self.datalim_to_dt()
    #     print("autoscale: dmin", dmin, ", dmax", dmax)
    #     delta = mdates.relativedelta(dmax, dmin)
    #     print("delta", delta)
    #     ret = mdates.RRuleLocator.autoscale(self)
    #     print("RRule:", ret)
    #     return ret


def daytime_formatter(d, pos=None):
    '''Custom matplotlib formatter:
       show the time of day except at midnight, when the date is shown.
       d is whatever units the locator returns; for dates, that has
       to be ordinal floats, so use num2date() to turn into datetime.
       As far as I can tell, this will be called for every tick the
       locator specifies, and returns a string to be displayed.
    '''
    # Empirically, pos is the X position (in some unkmnown coordinates)
    # when setting up axis tics. However, later, when locating mouse
    # positions, pos is None. So we can use pos t tell the difference
    # between locating and labeling, though this is undocumented
    # and may change at some point.
    # print("daytime_formatter:", d, type(d))
    d = mdates.num2date(d)
    if pos == None:
        # pos==None is when you're moving the mouse interactively;
        # always want an indicator for that.
        return d.strftime("%b %d %H:%M")

    if d.hour == 0:
        return d.strftime("%m/%d %H:%M")
    return d.strftime("%H:%M")


def smart_date_formatter_x(ax):
    '''Major and minor formatter/locators for labeling any plot
       with dates along the X axis.
       Tries to be smart about scaling.
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

    # Major labels once a day:
    ax.xaxis.set_major_locator(smart_date_locator())
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(daytime_formatter))

    ax.tick_params(which='major', length=12, color='k')
    # Or set it separately for the major and ticks:
    # plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    # ax1.set_xticklabels(xticklabels, rotation = 45, ha="right")

    # Minor labels:
    ax.xaxis.set_minor_locator(smart_date_locator(minor=True))
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

        smart_date_formatter_x(ax)

        fig.tight_layout(pad=1.0, w_pad=10.0, h_pad=.5)

        plt.show()

    # One week, by hour
    xvals = []
    start = datetime.datetime(2017, 1, 1)
    for i in range(7 * 24):
        xvals.append(start + datetime.timedelta(hours=i))
    print("start", xvals[0].strftime('%Y-%m-%d %H:%M'),
          "end", xvals[-1].strftime('%Y-%m-%d %H:%M'))
    plot_vs_dates(xvals)

    # # One month, by day
    # xvals = []
    # start = datetime.datetime(2017, 1, 1)
    # for i in range(31):
    #     xvals.append(start + datetime.timedelta(hours=i*24))

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
