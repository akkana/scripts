#!/usr/bin/env python3

# hotdog: watch the temperature, and when it gets near critical,
# suspend any CPU-intensive process.

import subprocess
import json
import re
import psutil
from pprint import pprint
import sys

def read_sensors():
    '''Read and parse the output of lm-sensors' sensors -j
       Returns a dictionary.
    '''
    proc = subprocess.Popen(["/usr/bin/sensors", "-j"], shell=False,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # proc.communicate() returns bytes, so change them to strings:
    return (json.loads(proc.communicate()[0].decode()))

def fetch_temps(sensors):
    # temps will be a list of quads: (name, input, max, crit)
    temps = []

    # I don't understand the partitioning sensors uses, hence the unclear names:
    for thing in sensors:
        for dev in sensors[thing]:
            # print("dev:", dev, type(sensors[thing][dev]))
            if type(sensors[thing][dev]) is str:
                continue
            # sensors can't use consistent keys: it uses things like
            # temp1_input, temp3_max etc. Sheesh.
            tinput = 0
            tmax = 0
            tcrit = 0
            for key in sensors[thing][dev]:
                # print("key:", key)
                if re.match('temp[0-9]+_input', key):
                    tinput = float(sensors[thing][dev][key])
                    # print("Set input to", tinput)
                elif re.match('temp[0-9]+_max', key):
                    tmax = float(sensors[thing][dev][key])
                elif re.match('temp[0-9]+_crit', key):
                    tcrit = float(sensors[thing][dev][key])

            if not tinput or (not tmax and not tcrit):
                continue
            if not tmax:
                tmax = tcrit
            elif not tcrit:
                tcrit = tmax
            temps.append((dev, tinput, tmax, tcrit))

    return temps

def overtemp(temps):
    '''Are any of the temperatures excessive?
    '''
    for quad in temps:
        if quad[1] > quad[2]:
            return True
    return False

def proclist():
    # Unfortunately there doesn't seem to be any way to get CPU percentage.
    # process.cpu_percent() always returns 0.0, even for VLC showing a
    # scaled video, or for Firefox.
    # We can get the cumulative CPU times; but that's not all that
    # helpful because it penalizes processes that have been running
    # for a long time.
    # MIght be able to do something with process.create_time(), though.
    procs = []
    for process in psutil.process_iter():
        # This doesn't work, even very active processes can
        # show up as 'sleeping'.
        if True or process.status() == 'running':
            procs.append((process.name(), sum(process.cpu_times())))

        # as_dict() is the easiest way to find out what's available.
        if 'vlc' in process.name():
            pd = process.as_dict()
            pd['memory_maps'] = 'xxx'
            pd['threads'] = 'xxx'
            pd['environ'] = 'xxx'
            pprint(pd)
        print(process.name(), process.status(), process.cpu_percent())

    procs.sort(key=lambda x: x[1], reverse=True)
    return procs

if __name__ == '__main__':
    j = read_sensors()
    # pprint(j)
    temps = fetch_temps(j)

    print("Temps")
    for quad in temps:
        print("%15s: %f (%f max, %f crit)" % quad)

    procs = proclist()
    print("Procs")
    for p in procs[:10]:
        print("%15s: %ds" % p)

