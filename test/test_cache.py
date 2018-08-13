#!/usr/bin/env python3

import unittest

import os
import datetime

from cachefile import Cachefile

class TestCache(Cachefile):
    # def __init__(self, cachedir):
    #     super(TestCache, self).__init__(cachedir)

    def apply_types(self, row):
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


    def test_cache(self):
        test_date = datetime.datetime(2018, 8, 1, 12, 0)
        self.cache.get_data(test_date)

        self.assertEqual(self.cache.cachedir,
                    os.path.expanduser('~/.config/test-cachefile'))

        cachefile = os.path.join(self.cache.cachedir,
                                 test_date.strftime('%Y-%m-%d'))
        assert os.path.exists(cachefile)

        with open(cachefile) as fp:
            file_contents = fp.read()
        self.assertEqual(file_contents, '''time,int,str,float
2018-08-01 01:00:00,42,"Hello, world",0.001
2018-08-01 13:00:00,99,Goodbye,1000.0
''')


    def test_file_locking(self):
        # test_date = datetime.datetime(2018, 8, 1, 12, 0)
        # self.cache.get_data(test_date)
        self.cache.keys = [ "time", "one", "two" ]

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


if __name__ == '__main__':
    unittest.main()

