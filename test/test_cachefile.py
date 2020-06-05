#!/usr/bin/env python3

# Tests for cachefile.py

### Some tweaks to make it work with Python2, for web servers without 3:
from __future__ import print_function

try:
    PermissionError
except NameError:
    PermissionError = OSError

### end Python2 tweaks

import unittest

import os
import datetime

from cachefile import Cachefile

class TestCache(Cachefile):
    def __init__(self, cachedir):
        super(TestCache, self).__init__(cachedir)

    def apply_types(self, row):
        row[self.TIME] = self.parse_time(row[self.TIME])
        row['int'] = int(row['int'])
        row['float'] = float(row['float'])

    def fetch_one_day_data(self, day):
        if day.year == 2018 and \
           day.month == 8 and day.day == 1:
            return [ { 'time': datetime.datetime(2018, 8, 1, 1, 0, 0),
                       'int': 42, 'str': "Hello, world", 'float':.001 },
                     {  'time': datetime.datetime(2018, 8, 1, 13, 0, 0),
                        'int': 99, 'str': "Goodbye", 'float': 1000. }
                   ]
        elif day.year == 2018 and day.month == 2:
            return [{ 'time': datetime.datetime(2018, 2, day.day,
                                                         hour, 0, 0),
                               'int': hour, 'str': "Hello, world",
                               'float': day.day + hour/100. } for hour in range(24)]
        else:
            morning = self.day_start(day)
            return [ { 'time': morning + datetime.timedelta(hours=2),
                       'int': 42, 'str': "Hello, world", 'float': .001 },
                     {  'time': morning + datetime.timedelta(hours=14),
                        'int': 99, 'str': "Goodbye", 'float': 1000.5 }
                   ]

    def clean_cachedir(self):
        '''Remove all cache files from the cachedir.
        '''
        if not os.path.exists(self.cachedir):
            return

        for f in os.listdir(self.cachedir):
            os.unlink(os.path.join(self.cachedir, f))
        os.rmdir(self.cachedir)


class CacheTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(CacheTests, self).__init__(*args, **kwargs)

        self.cache = TestCache("test-cachefile")

    # executed prior to each test
    def setUp(self):
        self.cache.clean_cachedir()

    # executed after each test
    def tearDown(self):
        self.cache.clean_cachedir()


    def test_cache_just_starttime(self):
        # Make sure cachefile is created

        # Python2 csv.DictWriter doesn't preserve field order.
        self.cache.fieldnames = [ 'time', 'int', 'str', 'float' ]

        test_date = datetime.datetime(2018, 8, 1, 12, 0)
        self.cache.get_data(test_date)

        self.assertEqual(self.cache.cachedir,
                    os.path.expanduser('~/.cache/test-cachefile'))

        cachefile = os.path.join(self.cache.cachedir,
                                 test_date.strftime('%Y-%m-%d') + ".csv")
        assert os.path.exists(cachefile)

        with open(cachefile) as fp:
            file_contents = fp.read()

        self.assertEqual(file_contents, '''time,int,str,float
2018-08-01 01:00:00,42,"Hello, world",0.001
2018-08-01 13:00:00,99,Goodbye,1000.0
''')

    def test_cache_no_times(self):
        # Test fetching with no time specified
        now = datetime.datetime.now()
        data = self.cache.get_data()
        for d in data:
            self.assertEqual(d['time'].year,   now.year)
            self.assertEqual(d['time'].month,  now.month)
            self.assertEqual(d['time'].day,    now.day)

        cachefile = os.path.join(self.cache.cachedir,
                                 now.strftime('%Y-%m-%d') + ".csv")
        assert os.path.exists(cachefile)


    def test_multiple_days(self):
        starttime = datetime.datetime(2018, 2, 10, 0, 0)
        endtime   = datetime.datetime(2018, 2, 12, 12, 0)
        data = self.cache.get_data(starttime, endtime)

        # Make sure we got data from the full range:
        self.assertEqual(data[0],
                         {'time': datetime.datetime(2018, 2, 10, 0, 0),
                          'int': 0,
                          'str': 'Hello, world',
                          'float': 10.0})
        self.assertEqual(data[32],
                         {'time': datetime.datetime(2018, 2, 11, 8, 0),
                          'int': 8,
                          'str': 'Hello, world',
                          'float': 11.08})
        self.assertEqual(data[-1],
                         {'time': datetime.datetime(2018, 2, 12, 23, 0),
                          'int': 23,
                          'str': 'Hello, world',
                          'float': 12.23})

        # and that we cached data for all those days:
        assert os.path.exists(os.path.join(self.cache.cachedir,
                                           '2018-02-10.csv'))
        assert os.path.exists(os.path.join(self.cache.cachedir,
                                           '2018-02-11.csv'))
        assert os.path.exists(os.path.join(self.cache.cachedir,
                                           '2018-02-12.csv'))

    def test_file_locking(self):
        # test_date = datetime.datetime(2018, 8, 1, 12, 0)
        # self.cache.get_data(test_date)
        self.cache.fieldnames = [ "time", "one", "two" ]

        cachefile = "/tmp/cachetest"
        try:
            os.unlink(cachefile)
        except:
            pass
        realfp = self.cache.open_cache_file(cachefile)

        self.cache.write_cache_line(realfp, { "time":
                                              datetime.datetime(2018, 8, 1,
                                                                1, 0),
                                              "one": 1,
                                              "two": 2 })

        with self.assertRaises(PermissionError):
            secondfp = self.cache.open_cache_file("/tmp/cachetest")

        self.cache.write_cache_line(realfp, { "time":
                                              datetime.datetime(2018, 8, 1,
                                                                13, 0),
                                              "one": 11,
                                              "two": 22 })

        with self.assertRaises(PermissionError):
            thirdfp = self.cache.open_cache_file("/tmp/cachetest")

        realfp.close()

        with open(cachefile) as fp:
            file_contents = fp.read()
        self.assertEqual(file_contents, '''time,one,two
2018-08-01 01:00:00,1,2
2018-08-01 13:00:00,11,22
''')

    def test_start_and_end_times(self):
        # XXX Test day_start and day_end
        # and test get_data() without start, end or both times
        # and make sure it fetches data for the proper dates.
        # Maybe make a class that returns date, year, month, day, hour, min, sec

        midday = datetime.datetime(2018, 7, 15, 13, 0)
        prevday = midday.replace(day = midday.day - 1)
        nextday = midday.replace(day = midday.day + 1)
        later = midday.replace(hour = 21)

        # Test starttime only
        starttime, endtime = self.cache.time_bounds(starttime=midday)
        self.assertEqual(starttime.year, midday.year)
        self.assertEqual(starttime.month, midday.month)
        self.assertEqual(starttime.day, midday.day)
        self.assertEqual(starttime.hour, midday.hour)
        self.assertEqual(starttime.minute, 0)
        self.assertEqual(endtime.year, midday.year)
        self.assertEqual(endtime.month, midday.month)
        self.assertEqual(endtime.day, midday.day)
        self.assertEqual(endtime.hour, 23)
        self.assertEqual(endtime.minute, 59)

        # Test full day
        starttime, endtime = self.cache.time_bounds(day=midday)
        self.assertEqual(starttime.year, midday.year)
        self.assertEqual(starttime.month, midday.month)
        self.assertEqual(starttime.day, midday.day)
        self.assertEqual(starttime.hour, 0)
        self.assertEqual(starttime.minute, 0)
        self.assertEqual(endtime.year, midday.year)
        self.assertEqual(endtime.month, midday.month)
        self.assertEqual(endtime.day, midday.day)
        self.assertEqual(endtime.hour, 23)
        self.assertEqual(endtime.minute, 59)

        # Test endtime only
        starttime, endtime = self.cache.time_bounds(endtime=midday)
        self.assertEqual(starttime.year, midday.year)
        self.assertEqual(starttime.month, midday.month)
        self.assertEqual(starttime.day, midday.day)
        self.assertEqual(starttime.hour, 0)
        self.assertEqual(starttime.minute, 0)
        self.assertEqual(endtime.year, midday.year)
        self.assertEqual(endtime.month, midday.month)
        self.assertEqual(endtime.day, midday.day)
        self.assertEqual(endtime.hour, midday.hour)
        self.assertEqual(endtime.minute, midday.minute)

        # Test endtime on an earlier day
        with self.assertRaises(ValueError):
            starttime, endtime = self.cache.time_bounds(starttime=midday,
                                                        endtime=prevday)

        # Test endtime on a later day
        with self.assertRaises(ValueError):
            starttime, endtime = self.cache.time_bounds(starttime=midday,
                                                        endtime=nextday)

        # Test full day with now
        starttime, endtime = self.cache.time_bounds(day=midday, now=midday)
        self.assertEqual(starttime.year, midday.year)
        self.assertEqual(starttime.month, midday.month)
        self.assertEqual(starttime.day, midday.day)
        self.assertEqual(starttime.hour, 0)
        self.assertEqual(starttime.minute, 0)
        self.assertEqual(endtime.year, midday.year)
        self.assertEqual(endtime.month, midday.month)
        self.assertEqual(endtime.day, midday.day)
        self.assertEqual(endtime.hour, midday.hour)
        self.assertEqual(endtime.minute, midday.minute)

        # Test end time later than now
        starttime, endtime = self.cache.time_bounds(starttime=midday,
                                                    endtime=later,
                                                    now=midday)
        self.assertEqual(starttime.year, midday.year)
        self.assertEqual(starttime.month, midday.month)
        self.assertEqual(starttime.day, midday.day)
        self.assertEqual(starttime.hour, midday.hour)
        self.assertEqual(starttime.minute, midday.minute)
        self.assertEqual(endtime.year, midday.year)
        self.assertEqual(endtime.month, midday.month)
        self.assertEqual(endtime.day, midday.day)
        self.assertEqual(endtime.hour, midday.hour)
        self.assertEqual(endtime.minute, midday.minute)


if __name__ == '__main__':
    unittest.main()

