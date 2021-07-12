#!/usr/bin/env python3

import sys
import os

import datetime
from dateutil.relativedelta import relativedelta

import requests

import matplotlib as mpl
import matplotlib.pyplot as plt


# LANL hasn't bothered to get their TLS certificate right.
# Disable the endless warnings:
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# LANL error messages, like "System Unavailable", are unfortunately
# served as HTML rather than something more easily parseable.
from bs4 import BeautifulSoup


def c_to_f(t):
    return t * (212.-32.) / 100. + 32.


def to_date(d):
    """Make sure d is a datetime.date.
       This is ridiculously difficult to do with datetime,
       because datetime.date can't be initialized from a datetime
       but datetime.date doesn't have a date() method.
    """
    if hasattr(d, "date"):
        return d.date()
    return d


def maxnone(data):
    return max([x for x in data if x is not None])


class LANLWeather(object):
    """Fetch and parse data from the LANL weather machine.
    """

    def __init__(self, tower, start, end, keys):
        self.tower = tower
        self.keys = keys

        if hasattr(start, 'year'):
            self.start = datetime.date(start.year, start.month, start.day)
        else:
            self.start = datetime.date(*start)

        if not hasattr(end, 'year'):
            self.end = datetime.date(*end)
        else:
            self.end = end
        # But the LANL weather machine barfs on requests with an end time
        # more recent than 2 hours ago. So make sure it's earlier:
        # now = datetime.datetime.now()
        # if (now - self.end).seconds < 7200:
        #     self.end = now - datetime.timedelta(seconds=7200)

        # Where does the data end? Might not be the same as self.end.
        self.realend = self.start

        self.data = {}
        self.dates = []

        # Set up cache directory. Default: ~/.cache/lanlweather
        # but you can change it with the env var LANLWEATHER
        self.cachedir = os.getenv("LANLWEATHER")
        if not self.cachedir:
            self.cachedir = os.path.expanduser("~/.cache/lanlweather")

    request_keys = [ 'spd1', 'spd2', 'spd3', # Speeds at 12, 23 and 46 m height
                     'sdspd1', 'sdspd2', 'sdspd3', # sdev of wind speeds
                     'dir1', 'dir2', 'dir3', # wind directions 12, 23, 46 m
                     'sddir1', 'sddir2', 'sddir3', # sdev of wind directions
                     'w1', 'w2', 'w3',       # vertical wind speeds
                     'sdw1', 'sdw2', 'sdw3', # stdev of vertical wind sp
                     'fvel2',                # friction velocity
                     'temp0', 'temp1', 'temp2', 'temp3', # temps 1.2, 12, 23, 46
                     'press',                # pressure
                     'rh', 'ah',             # rel and abs humidity
                     'dewp', 'precip',       # dew point, precipitation
                     'swdn', 'swup',         # shortwave radiation down/up
                     'lwdn', 'lwup',         # longwave radiation down/up
                     'netrad',               # net radiation
                     'sheat', 'lheat',       # sensible/latent heatflux
                     'stemp1', 'stemp2', 'stemp3',# soil temp -.02, -.06, -.10 m
                     'smoist1', 'smoist2',   # soil moisture 0 to 0.8, 0 to -.15
                     'gheat'                 # ground heat flux
    ]

    # List of towers that offer 15-minute reports.
    # This hasn't been checked. Some tower names may be wrong.
    towers = [ 'mcdn',       # may be ta5
               'ta6', 'ta49', 'ta53', 'ta54',
               'ncom',       # North Community
             ]


    def get_data(self):
        """Get data from cache if possible. If it's not cached,
           make net data requests to the weather machine.
           Make a separate request for each month,
           since the weather machine refuses requests for more than 3 months.
           Use the tower and start/end dates already set in self.

           We'll request full months even if less is requested,
           and we'll request all keys even if we don't need them all,
           so we can keep a more complete cache.
        """

        # Loop over months requested.
        # Start on the first of the month specified by startdate:
        startday = self.start.replace(day=1)

        # Loop over requested months
        while True:
            cachefile = os.path.join(self.cachedir,
                                     "%04d-%02d-%s.csv" % (startday.year,
                                                           startday.month,
                                                           self.tower))
            # See if this month and year is already cached.
            datablob = None
            if os.path.exists(cachefile):
                with open(cachefile) as fp:
                    datablob = fp.read()
                    print("Read from cache file", cachefile)
                    lines = datablob.split('\n')
                    # If the file ends with a newline (as it will),
                    # split('\n') will give us a spurious empty final line.
                    if not lines[-1].strip():
                        del lines[-1]

                    # But does it cover the entire month?
                    filestart, fileend = self.get_start_end_dates(lines)

                    # Is filestart > 1, or fileend < last day of month?
                    last_day_of_month = (datetime.datetime(fileend.year,
                                                           fileend.month%12 + 1,
                                                           1)
                                         - datetime.timedelta(days=1))

                    # If the file is missing days from the given month,
                    # re-fetch it to get the missing days --
                    # but if it goes far enough to include today's date,
                    # don't re-fetch even if it doesn't have all of today.
                    # We can always fetch again tomorrow.
                    if (filestart.day > 1 or
                        (fileend.day < last_day_of_month.day
                         and fileend.date() < datetime.date.today())):
                        # Zero out datablob and lines so we'll fetch
                        # the whole month again.
                        print("Cache file only contained " \
                              "%04d-%02d-%02d through " \
                              "%04d-%02d-%02d" % (filestart.year,
                                                  filestart.month,
                                                  filestart.day,
                                                  fileend.year,
                                                  fileend.month,
                                                  fileend.day))
                        print("Fetching month %d-%d again" % (startday.year,
                                                              startday.month))
                        datablob = None
                        lines = None

            if not datablob:
                print("Making request for", startday.year, startday.month)

                datablob = self.make_lanl_request(self.tower,
                                                  startday.year, startday.month)

                # Don't save to cache quite yet: it may not be actual CSV.
                # But make sure the directory is there.
                if not os.path.exists(self.cachedir):
                    os.makedirs(self.cachedir)

            try:
                lines = datablob.split('\n')

                self.parse_lanl_data(lines)

                # Now, if parsing worked without errors, it's okay to
                # save to a cached CSV file.
                if not os.path.exists(cachefile):
                    with open(cachefile, "w") as outfile:
                        outfile.write(datablob)
                        print(("Saved to cache %s" % cachefile))

            except Exception as e:
                print("Couldn't parse blob in", cachefile)
                print(str(e))

                # Save an error file
                htmlfilename = cachefile + '.html'
                with open(htmlfilename, "w") as htmlfile:
                    htmlfile.write(datablob)
                    print("Saved original file to", htmlfilename)

                # Try to parse the error message
                soup = BeautifulSoup(datablob, 'lxml')
                pagecontent = soup.find(id='pagecontent')
                try:
                    print(("HTML Error: %s" % pagecontent.text))
                except:
                    print("No error message but no data either")

                try:
                    os.unlink(cachefile)
                except:
                    print("Nothing to unlink")

                sys.exit(1)

            startday += relativedelta(months=1)
            if to_date(startday) > to_date(self.end):
                break


    def make_lanl_request(self, tower, year, month):
        """Make a data request for 15-minute data to the LANL weather machine.
           tower is a string, like 'ta54'
           keys is a list of keys we're interested in (see request_keys).
           start and end times can be either datetimes or [y, m, d, [h, m, s]]

           The weather machine will only return 3 months worth of 15-minute data
           at a time, and it lags: if you request data for anything in the
           last hour, it bails and returns an empty file.
        """
        # Figure out the end time for the request.
        # If it's this month, then we can only request data
        # up until about an hour ago.
        # Otherwise, we want everything until the end of the
        # last day of the month.
        now = datetime.datetime.now()
        if year == now.year and month == now.month:
            endtime = now - datetime.timedelta(hours=2)
        else:
            # set it to the first of the same month, at 23:59:
            endtime = datetime.datetime(year, month, 1, 23, 59)
            # bump it to the first of the next month:
            endtime += relativedelta(months=1)
            # set it to the last day of the previous (original) month:
            endtime -= datetime.timedelta(days=1)

        print("make lanl request:", year, month, "01 00:00 to", \
            endtime.year, endtime.month, endtime.day, \
            endtime.hour, endtime.minute)

        request_data = [
            ('tower', tower),
            ('format', 'tab'),
            ('type', '15'),
            ('access', 'extend'),
            ('SUBMIT_SIGNALS', 'Download Data'),

            ('startyear', '%04d' % year),
            ('startmonth', '%02d' % month),
            ('startday', '01'),
            ('starthour', '00'),
            ('startminute', '00'),

            ('endyear', '%04d' % endtime.year),
            ('endmonth', '%02d' % endtime.month),
            ('endday', '%02d' % endtime.day),
            ('endhour',  '%02d' % endtime.hour),
            ('endminute', '%02d' % endtime.minute),
        ]

        # Request everything, not just the keys we're plotting,
        # so we have everything cached for later.
        for key in LANLWeather.request_keys:
            request_data.append(('checkbox', key))

        # print("request data:", request_data)

        headers = {
            'User-Agent': 'LANL Weather Fetcher 0.9',
            'Referer': 'https://www.weather.lanl.gov/data_request_green_weather.asp',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        # Need verify=False in the request: www.weather.lanl.gov
        # has SSL set up improperly, among its many other problems.
        # r = requests.post('http://www.weather.lanl.gov/'
        #                   'data_request_green_weather.asp',
        #                   data=request_data, headers=headers, verify=False)
        LANL_URL = 'https://www.weather.lanl.gov/data_request_green_weather.asp'
        try:
            r = requests.post(LANL_URL,
                          headers=headers, # cookies=cookies,
                          data=request_data, verify=False)
        except requests.exceptions.ConnectionError:
            print("Connection Error on", LANL_URL)
            from pprint import pprint
            print("Headers:")
            pprint(headers)
            print("Request data:")
            pprint(request_data)
            sys.exit(1)

        if not r.text:
            raise RuntimeError("Empty response!")

        return r.text


    def get_fields_and_units(self, lines):
        """In LANL data, there's a bunch of boilerplate stuff in the first
           four lines, so the fields don't come until the fifth line,
           then the sixth line is units. So we can't use the normal
           CSV reader. Return fields, units (two lists of str).
        """
        # Find the indices in the data for each key we're interested in.
        fields = lines[5].split('\t')
        units = lines[6].split('\t')
        return fields, units

    def get_start_end_dates(self, lines):
        """Do part of what parse_lanl_data does, only for the
           first and last lines, and return two datetimes.
        """
        fields, units = self.get_fields_and_units(lines)

        # We'll need to know the indices for the time values.
        year = fields.index('year')
        month = fields.index('month')
        day = fields.index('day')
        hour = fields.index('hour')
        minute = fields.index('minute')

        l = lines[7].split('\t')
        startdate = datetime.datetime(int(l[year]), int(l[month]), int(l[day]),
                                      int(l[hour]), int(l[minute]), 0)
        l = lines[-1].split('\t')
        enddate = datetime.datetime(int(l[year]), int(l[month]), int(l[day]),
                                    int(l[hour]), int(l[minute]), 0)

        return startdate, enddate


    def parse_lanl_data(self, lines):
        """Take a list of lines read either from a cache file
           or a net request, parse them and add them to self.data.
        """
        fields, units = self.get_fields_and_units(lines)

        # indices will be a list paralleling self.keys,
        # saving the index of each key in the data table we're reading.
        indices = []

        for i, k in enumerate(self.keys):
            idx = fields.index(k)
            if idx <= 0:
                raise IndexError(k + " is not in dataset")
            indices.append(idx)

            # initialize a vector of values for that key, if not already there:
            if k not in self.data:
                self.data[k] = []

        # We'll also need to know the indices for the time values.
        year = fields.index('year')
        month = fields.index('month')
        day = fields.index('day')
        hour = fields.index('hour')
        minute = fields.index('minute')

        for line in lines[7:]:
            line = line.strip()
            if not line:
                continue
            l = line.split('\t')
            d = datetime.datetime(int(l[year]), int(l[month]), int(l[day]),
                                  int(l[hour]), int(l[minute]), 0)
            if self.dates and d <= self.dates[-1]:
                print("WARNING! Dates out of order,", d, "<=", self.dates[-1])
            self.dates.append(d)
            for i, k in enumerate(self.keys):
                idx = indices[i]

                # Missing data is denoted with a * in LANL data.
                # Use None in self.data.
                # Matplotlib is supposed to show None as a break:
                # https://matplotlib.org/2.0.2/examples/pylab_examples/nan_test.html
                # That doesn't actually work for me (maybe it only works with
                # np.nan), but at least matplotlib no longer dies on None.
                if not l[idx] or l[idx] == '*':
                    # print("Missing data for", k, "on", d)
                    self.data[k].append(None)

                # convert temps C -> F
                elif k.startswith('temp'):
                    self.data[k].append(c_to_f(float(l[idx])))

                else:
                    self.data[k].append(float(l[idx]))

        # We'll scale to self.end, so in case we rounded down,
        # reset self.end so we don't have extra whitespace on the plot.
        if to_date(self.dates[-1]) > to_date(self.realend):
            self.realend = self.dates[-1]

    def find_maxmin(self, key):
        """Find the daily maximum for the more granular data in key.
           Save it as key_max and key_min, e.g. self.data['temp0_max'].
           Return key_days, key_max, key_min
        """
        key_max = key + "_max"
        key_min = key + "_min"
        key_days = key + "_days"

        self.data[key_min] = []
        self.data[key_max] = []
        self.data[key_days] = []

        curday = None

        def end_of_day():
            """Called for each new day, and at the end,
               to store the current valmin and valmax.
            """
            if not curday:
                return

            # if curday.month == 6 or curday.month == 7 and curday.year == 2020:
            #     print(curday, valmin)

            if valmin != sys.float_info.max and \
               valmax !=sys.float_info.min:
                self.data[key_min].append(valmin)
                self.data[key_max].append(valmax)
                self.data[key_days].append(curday)
            else:
                print("No data on", curday)

        for dt, val in zip(self.dates, self.data[key]):
            newday = dt.date()
            if newday != curday:
                end_of_day()
                curday = newday
                valmin = sys.float_info.max
                valmax = sys.float_info.min
            if val:    # If data isn't missing
                valmin = min(valmin, val)
                valmax = max(valmax, val)

        end_of_day()

        return key_days, key_max, key_min


class LANLWeatherPlots(LANLWeather):
    """Plot (as well as fetch and parse) data from the LANL weather machine.
    """

    def __init__(self, tower, start, end, keys):
        super(LANLWeatherPlots, self).__init__(tower, start, end, keys)
        self.fig = plt.figure(figsize=(15, 5))

        self.ax1 = None
        self.ax3 = None


    def show(self):
        # Various desperate attempts to trim spurious whitespace:

        # Nothing in adjust() makes any difference.
        # (Also tried calling plt.subplots_adjust(), no change.)
        # self.fig.subplots_adjust(left=0.1, right=0.11, top=0.9, bottom=0.1,
        #                          hspace=0.1)

        # This also does nothing, except interfere with earlier set_ylim calls.
        # plt.axis('tight')
        # self.ax1.axis('tight')
        # self.ax3.axis('tight')

        # Nor does this:
        # self.ax1.set_adjustable('box-forced')
        # self.ax3.set_adjustable('box-forced')

        # This gets rid of the intra-plot whitespace:
        if self.ax1:
            self.ax1.set_xlim([self.start, self.realend])
        if self.ax3:
            self.ax3.set_xlim([self.start, self.realend])

        # This gets rid of some of the extra whitespace between/around plots.
        # pad controls padding at the top, bottom and sides;
        # w_pad does nothing I can see -- I think it's space between
        # plots horizontally if there are more than two columns;
        # h_pad seems to control the space between the plots vertically.
        # There doesn't seem to be a way to allow enough space at the top
        # for the top legend without also adding a bunch of unneeded
        # whitespace at the sides and bottom.
        plt.tight_layout(pad=2.0, w_pad=10.0, h_pad=3.0)

        plt.show()


    def plot_seasonal_wind(self, ws):
        """
        Plot wind speed by season, averaging over all available years.
        Required input:
            ws: Key used for Wind speeds (knots)
        Optional Input:
        """

        # Loop over all dates we know about, building an average of the
        # wind for that day of the year.
        avs = [0.0] * 366
        datapoints = [0] * 366
        for i, d in enumerate(self.dates):
            day_of_year = d.timetuple().tm_yday - 1
            # print("Day of year", day_of_year, "timetuple", d.timetuple())
            if self.data[ws][i]:
                avs[day_of_year] += self.data[ws][i]
                # XXX Note that this will be off by a day in non leap years.
                datapoints[day_of_year] += 1

        for d, dp in enumerate(datapoints):
            if dp:
                avs[d] /= dp

        curyear = datetime.date.today().year
        days = [ datetime.date(curyear, 1, 1) + datetime.timedelta(d)
                 for d, dp in enumerate(datapoints) ]

        plt.plot(days, avs, # '.',
                 color="green", label='Average wind speed')

        plt.ylabel('Date (ignore year)')
        plt.ylabel('Wind speed average for day')
        plt.legend(loc='upper left')

    def plot_winds(self, ws, wd):
        """
        Required input:
            ws: Key used for Wind speeds (knots)
            wd: Key used for Wind direction (degrees)
        Optional Input:
        """
        # Plot the wind directions first: want it underneath
        # so it doesn't overwhelm the wind speed plot.
        self.ax1 = self.fig.add_subplot(2, 1, 1)   # nrows, ncols, plotnum
        ln1 = self.ax1.plot(self.dates, self.data[wd],
                            '.', color="orange", label='Wind Direction')

        plt.ylabel('Wind Direction\n(degrees)', multialignment='center')
        self.ax1.set_ylim([0, 360])
        # plt.yticks([45, 135, 225, 315], ['NE', 'SE', 'SW', 'NW'])
        plt.yticks([0, 90, 180, 270, 360], ['N', 'E', 'S', 'W', 'N'])

        plt.grid(b=True, which='major', axis='y', color='k',
                 linestyle='--', linewidth=0.5)

        plt.setp(self.ax1.get_xticklabels(), visible=True)

        # Plot wind speed on top of wind direction
        axtwin = self.ax1.twinx()
        ln2 = axtwin.plot(self.dates, self.data[ws],
                          color='b', label='Wind Speed')
        plt.ylabel('Wind Speed (knots)', multialignment='center')
        axtwin.set_ylim([0, maxnone(self.data[ws])])

        # Top label
        lns = ln1 + ln2
        labs = [l.get_label() for l in lns]
        axtwin.legend(lns, labs, loc='upper center',
                      bbox_to_anchor=(0.5, 1.2), ncol=3, prop={'size': 12})

    def plot_temp(self, temp, plot_range=None):
        self.ax3 = self.fig.add_subplot(2, 1, 2, sharex=self.ax1)
        self.ax3.plot(self.dates, self.data[temp],
                      '-', color='blue', label='Ground temperature')
        self.ax3.legend(loc='upper center', bbox_to_anchor=(0.5, 1.22),
                        prop={'size': 12})
        plt.setp(self.ax3.get_xticklabels(), visible=True)
        plt.grid(b=True, which='major', axis='y', color='k',
                 linestyle='--', linewidth=0.5)
        plt.ylabel('Temperature', multialignment='center')

        # set_ylim is ignored if you do it this early.
        # It works if you call it later, just before plt.show().
        self.ax3.set_ylim(0, maxnone(self.data[temp]), 4)

        # Add a horizontal line for freezing
        plt.axhline(y=32, linewidth=.5, linestyle="dashed", color='r')

    def plot_maxmin(self, key):
        """Plot the daily maximum for the more granular data in key."""
        key_days, key_max, key_min = self.find_maxmin(key)

        self.ax3 = self.fig.add_subplot(1, 1, 1, sharex=self.ax1)
        self.ax3.plot(self.data[key_days], self.data[key_max],
                      '-', color='red', label='Max daily temp')
        self.ax3.plot(self.data[key_days], self.data[key_min],
                      '-', color='blue', label='Min daily temp')
        self.ax3.legend(loc='upper left', prop={'size': 12})
        plt.setp(self.ax3.get_xticklabels(), visible=True)
        plt.grid(b=True, which='major', axis='y', color='k',
                 linestyle='--', linewidth=0.5)
        plt.ylabel('Temperature', multialignment='center')

        # set_ylim is ignored if you do it this early.
        # It works if you call it later, just before plt.show().
        self.ax3.set_ylim(0, max(self.data[key_max]), 4)

        # Add a horizontal line for freezing
        plt.axhline(y=32, linewidth=.5, linestyle="dashed", color='r')


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', "--start", dest="start_date", default=None,
                        help="Start date, YYYY-MM-DD, "
                             "default beginning of end year",
                        type=lambda s: datetime.datetime.strptime(s,
                                                                  '%Y-%m-%d'))
    parser.add_argument('-e', "--end", dest="end_date", default=None,
                        help="End date, YYYY-MM-DD, "
                             "default yesterday",
                        type=lambda s: datetime.datetime.strptime(s,
                                                                  '%Y-%m-%d'))
    # Types of plots
    parser.add_argument('-m', "--maxmin", dest="maxmin",
                        default=False,
                        help="Plot daily max/min temperatures",
                        action="store_true")

    parser.add_argument('-w', "--seasonal_wind", dest="seasonal_wind",
                        default=False,
                        help="Plot seasonal winds",
                        action="store_true")

    args = parser.parse_args(sys.argv[1:])
    # print("args:", args)

    if not args.end_date:
        args.end_date = datetime.datetime.now()

    if not args.start_date:
        args.start_date = datetime.datetime(args.end_date.year, 1, 1)

    if args.end_date <= args.start_date:
        print("Error: start date", args.start_date,
              "must be earlier than end date", args.end_date)
        sys.exit(1)

    lwp = LANLWeatherPlots('ta54', args.start_date, args.end_date,
                           ["spd1", "dir1", "temp0"])

    lwp.get_data()

    if args.maxmin:
        lwp.plot_maxmin('temp0')

    elif args.seasonal_wind:
        lwp.plot_seasonal_wind('spd1')

    else:
        lwp.plot_winds('spd1', 'dir1')
        lwp.plot_temp('temp0')

    lwp.show()


if __name__ == '__main__':
    main()

