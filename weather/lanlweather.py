#!/usr/bin/env python

import datetime
import requests

request_keys = [ 'spd1', 'spd2', 'spd3',    # Speeds at 12, 23 and 46 m height
                 'sdspd1', 'sdspd2', 'sdspd3', # sdev of wind speeds
                 'dir1', 'dir2', 'dir3',    # wind directions 12, 23, 46 m
                 'sddir1', 'sddir2', 'sddir3', # sdev of wind directions
                 'w1', 'w2', 'w3',          # vertical wind speeds
                 'sdw1', 'sdw2', 'sdw3',    # stdev of vertical wind sp
                 'fvel2',                   # friction velocity
                 'temp0', 'temp1', 'temp2', 'temp3',  # temps 1.2, 12, 23, 46
                 'press',                   # pressure
                 'rh', 'ah',                # rel and abs humidity
                 'dewp', 'precip',          # dew point, precipitation
                 'swdn', 'swup',            # shortwave radiation down/up
                 'lwdn', 'lwup',            # longwave radiation down/up
                 'netrad', 'sheat', 'lheat',# net rad, sensible/latent heatflux
                 'stemp1', 'stemp2', 'stemp3',  # soil temp -.02, -.06, -.10 m
                 'smoist1', 'smoist2',      # soil moisture 0 to 0.8, 0 to -.15
                 'gheat'                    # ground heat flux
]

def make_lanl_request(keys, starttime, endtime):
    # start and end times can be either datetimes or 
    if not hasattr(starttime, 'year'):
        starttime = datetime.datetime(*starttime)
    if not hasattr(endtime, 'year'):
        endtime = datetime.datetime(*endtime)
    request_data = { 'tower': 'ta54',
                     'format': 'tab',
                     'type': '15',
                     'access': 'extend',
                     'SUBMIT_SIGNALS': 'Download Data',

                     'startyear': '2017',
                     'startmonth': '03',
                     'startday': '01',
                     'starthour': '00',
                     'startminute': '00',

                     'endyear': '2017',
                     'endmonth': '03',
                     'endday': '15',
                     'endhour': '00',
                     'endminute': '00'
    }

    request_data['checkbox'] = ','.join(keys)

    r = requests.post('http://environweb.lanl.gov/weathermachine/data_request_green_weather.asp', data = request_data)

    lines = r.text.split('\n')
    return lines[7:], lines[5], lines[6]

if __name__ == '__main__':
    data, fields, units = make_lanl_request(["spd1", "temp0"],
                          [2017, 3, 20], datetime.datetime.now())

    # will want to split('\t') each of these, but for now:
    print fields
    print units
    for line in data:
        print line

