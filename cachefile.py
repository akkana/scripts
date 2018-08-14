#!/usr/bin/env python3

# Take dictionaries, fetched from a web API or wherever,
# cache them locally, and allow access that will transparently
# read from cache, if available, or fetch from the API.
# The cache will be a series of CSV files, one per day,
# with the date as one of the fields.

# To use it, subclass from Cachefile and redefine the following:
# fetch_one_day_data(self, day=None):
#      fetch one day's worth of data from the web API or wherever.
#      Will fetch for whatever day contains the given datetime.
# apply_types(self, row):
#     Given a row that was just read in as strings, change the items
#     to appropriate types, e.g. int, float, datetime etc.
# self.DATE: the name for the date field (default 'date').

import datetime
import csv
import os

class Cachefile:
    def __init__(self, cachedir):
        self.TIME = 'time'

        self.verbose = True

        self.keys = None
        self.writer = None

        if cachedir.startswith('/'):
            self.cachedir = cachedir

        else:
            self.cachedir = None
            # cachedir can be in ~/.cache/cachedir, or /var/cache/cachedir
            userdir = os.path.expanduser('~/.cache')
            for d in [ userdir, '/var/cache' ]:
                dpath = os.path.join(d, cachedir)
                if os.path.exists(dpath):
                    self.cachedir = dpath
                    break

            if not self.cachedir:
                self.cachedir = os.path.join(userdir, cachedir)


    def write_cache_file(self, day_data):
        '''Write (or overwrite) the whole cache file for the given day
           Otherwise, will overwrite the whole file.
        '''
        if not self.keys:
            self.keys = day_data[0].keys()

        # Make sure the data doesn't span more than one day.
        if day_data[0][self.TIME].day != day_data[-1][self.TIME].day:
            print("Can't cache data for multiple days: %s - %s" % (
                day_data[0][self.TIME].strftime('%Y-%M-%d'),
                day_data[-1][self.TIME].strftime('%Y-%M-%d')))
            return

        if not os.path.exists(self.cachedir):
            os.makedirs(self.cachedir)

        cachefile = os.path.join(self.cachedir,
                                 day_data[-1][self.TIME].strftime('%Y-%m-%d'))

        # Write to a temporary copy then move it into place.
        # This is deliberately not unique -- it'll be chmodded
        # as a locking mechanism, so only one instance of Cachefile
        # can make changes at once.
        tmpfile = cachefile + ".new"
        try:
            cachefp = self.open_cache_file(tmpfile)

            for item in day_data:
                self.write_cache_line(cachefp, item)

            cachefp.close()
            self.writer = None

            if self.verbose:
                print("Wrote cache file", cachefile)

            os.rename(tmpfile, cachefile)

        except PermissionError:
            print("Can't update temp file %s, it's locked" % tmpfile)
            os.system("ls -la " + self.cachedir)


    def open_cache_file(self, cachefile):
        # To avoid race conditions, use os.open to create the file
        # with a mode so that no one else can write to it.
        fp = open(os.open(cachefile,
                          os.O_CREAT | os.O_WRONLY, 0o444), 'w')

        self.writer = csv.DictWriter(fp, fieldnames=self.keys)
        self.writer.writeheader()

        return fp


    def write_cache_line(self, cachefp, item):
        '''Write one interval (one line) to a cache file.
        '''
        self.writer.writerow(item)


    # Cache files are organized by date, one per day:
    # ~/.cache/enphase/YYYY-MM-DD.dat
    # Inside each file are CSV lines: time,powr,enwh,devices_reporting
    def read_cache_file(self, day=None):
        '''Read the cache file for the given day (a datetime)
           and return the cache file name plus a list of dictionaries,
           one for each line.
        '''
        if not day:
            day = datetime.datetime.now()

        cachefile = os.path.join(self.cachedir, day.strftime('%Y-%m-%d'))
        data = []
        try:
            with open(cachefile) as csvfp:
                reader = csv.DictReader(csvfp)
                for row in reader:
                    self.apply_types(row)
                    # csv.DictReader reads everything as strings. Convert back.
                    data.append(row)
        except FileNotFoundError:
            # File isn't there yet, first run of the day?
            pass

        return cachefile, data


    def fetch_one_day_data(self, day):
        '''fetch_data, undefined in this base class, should fetch
           one day's data using whatever web or other API is appropriate.
           Override it in your derived class.
        '''
        raise RuntimeError("Don't know how to fetch: "
                           "override fetch_data in subclasses")
        pass


    def day_start(self, day):
        '''Given a datetime, return the beginning of that day as a datetime.
        '''
        return day.replace(hour=0, minute=0, second=0, microsecond=0)


    def day_end(self, day):
        '''Given a datetime, return the beginning of that day as a datetime.
        '''
        return day.replace(hour=23, minute=59, second=59, microsecond=0)


    def time_bounds(self, starttime=None, endtime=None, day=None, now=None):
        '''If day is specified, return the beginning and end of that day.
           Otherwise, if no starttime, set it to the beginning of today.
           If no endtime, set it to the end of today.
           In every case, restrict the time range to a single day,
           and don't allow anything later than now.
           now can be specified because it may need to be set back by some
           amount, like 10 minutes, depending on how often the API updates.
        '''
        if not now:
            now = datetime.datetime.now()

        if day:
            starttime = self.day_start(day)
            endtime = self.day_end(day)

        elif not starttime and not endtime:
            # Set back to the beginning of the day:
            starttime = self.day_start(now)
            # and end now.
            endtime = now

        elif not starttime:
            starttime = self.day_start(endtime)

        elif not endtime:
            # If we're starting today, end now:
            if starttime.year == now.year and starttime.month == now.month \
               and starttime.day == now.day:
                endtime = now
            # Else end at the end of the day we started:
            else:
                endtime = self.day_end(starttime)
        elif starttime.year != endtime.year \
             or starttime.month != endtime.month \
             or starttime.day != endtime.day:
            raise ValueError("time_bounds: %s and %s must start and end on the same day" % (endtime, starttime))

        if starttime > endtime:
            raise ValueError("endtime %s can't be earlier than starttime %s"
                             % (endtime, starttime))
        if endtime > now:
            endtime = now

        return starttime, endtime


    def get_data(self, starttime=None, endtime=None):
        '''Get a block of data between two datetimes,
           reading from cache when possible, otherwise fetching from API
           and writing new cache files.
           starttime defaults to midnight today.
           endtime defaults to now, or the end of the day of starttime.
        '''

        data = []

        # Loop over days, fetching one day's data at a time:
        while True:
            cachefile, cached_data = self.read_cache_file(starttime)

            # Do we already have enough cached?
            try:
                modtime = datetime.datetime.fromtimestamp(os.stat(cachefile).st_mtime)
            except:
                # Set a very early date:
                modtime = datetime.datetime(1, 1, 1, 0, 0)
            if cached_data and \
                modtime >= (endtime - datetime.timedelta(minutes=10)):
                data += cached_data
                if self.verbose:
                    print("We already have enough cached. Hooray!")

            else:
                if not endtime:
                    endtime = self.day_end(starttime)
                new_data = self.fetch_one_day_data(starttime)
                if self.verbose:
                    print("Fetched data from API", cachefile)

                # If the data is new, re-write the cache file,
                # protecting it with chmod though that still allows
                # for race conditions.

                # What's considered new?
                if cached_data:
                    lastcache = cached_data[-1][self.TIME]
                else:
                    lastcache = endtime.replace(hour=0, minute=0,
                                                second=0, microsecond=0)

                if new_data:
                    self.write_cache_file(new_data)

                    data += new_data

            # Next day.
            starttime += datetime.timedelta(days=1)
            if starttime >= endtime:
                break

        return data


if __name__ == '__main__':
    print("No main routine: Cachefile is only useful if you subclass it.")

