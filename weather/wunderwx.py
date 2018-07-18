#!/usr/bin/env python

from __future__ import print_function

# Weather from wunderground.
# Needs an API key, which is a pain in the butt to get even for the free one.
# Put your API key in ~/.config/wunderwx or set it in WUNDERKEY

import requests
import json
from pprint import pprint
import os, sys

# The global key
wunderkey = None

def find_nearby_stations(wundata):
    '''Extract the nearby stations info in the wunderground data
       into a sorted list.
    '''
    nearby = []

    # Ignore the list of official airport stations,
    # wundata['location']['nearby_weather_stations']['airport']['station']
    # since it doesn't give distance for those, and we can get them
    # from other sites anyway.

    stationlist = wundata['location']['nearby_weather_stations']['pws']['station']
    for station in stationlist:
        nearby.append((int(station['distance_mi']), station))

    return nearby

def init_key():
    global wunderkey
    wunderkey = os.getenv('WUNDERKEY')
    if not wunderkey:
        with open(os.path.expanduser('~/.config/wunderwx')) as fp:
            wunderkey = fp.read().strip()

    if not wunderkey:
        raise RuntimeError("Put your wunderground key in WUNDERKEY"
                           "or ~/.config/wunderwx.")

def get_stations_by_zip(zip):
    r = requests.get('http://api.wunderground.com/api/%s/geolookup/q/%s.json' % (wunderkey, zip))
    return json.loads(r.text)

def print_stations_by_zip(zip):
    stations = get_stations_by_zip(zip)
    # pprint(stations)
    print("Zip:", zip)
    print("County:", stations['location']['city'])
    for stationtype in stations['location']['nearby_weather_stations']:
        stationlist = stations['location']['nearby_weather_stations'][stationtype]['station']
        print()
        print("=== %s stations: ===" % stationtype)
        for station in stationlist:
            # pprint(station)
            if 'icao' in station and station['icao']:
                print('Airport %s: %s' % (station['icao'],
                                          station['city']))
            elif 'id' in station and 'neighborhood' in station \
                 and station['neighborhood']:
                print('ID %s: %s, %s' % (station['id'],
                                         station['neighborhood'],
                                         station['city']))
            else:
                print("Confusing station:")
                pprint(station)

def print_conditions(conditions):
    obs = conditions['current_observation']
    for item in obs:
        val = obs[item]
        if type(val) is int:
            print("    %s: %d" % (item, val))
        elif type(val) is float:
            print("    %s: %.1f" % (item, val))
        elif type(val) is str:
            print("    %s: %s" % (item, val))

def conditions_at_station(stationid):
    r = requests.get('http://api.wunderground.com/api/%s/conditions/q/pws:%s.json' % (wunderkey, stationid))
    conditions = json.loads(r.text)
    # pprint(conditions)
    return conditions

if __name__ == '__main__':
    init_key()

    if len(sys.argv[1]) == 5 and int(sys.argv[1]):
        zip = sys.argv[1]
        print_stations_by_zip(zip)
    else:
        station_id = sys.argv[1]
        cond = conditions_at_station(station_id)
        print("Station %s conditions:" % station_id)
        print_conditions(cond)

