#!/usr/bin/env python3

# Look up a comet and compute its position, using Skyfield.
# This is a brand new function in Skyfield!
# https://rhodesmill.org/skyfield/kepler-orbits.html

from skyfield.api import load
from skyfield.data import mpc
from skyfield.constants import GM_SUN_Pitjeva_2005_km3_s2 as GM_SUN

import dateutil.parser

import sys, os


with load.open(mpc.COMET_URL) as f:
    comets = mpc.load_comets_dataframe(f)

print(len(comets), 'comets loaded')

# Index by designation for fast lookup.
comets = comets.set_index('designation', drop=False)

ts = load.timescale(builtin=True)
eph = load('de421.bsp')
sun = eph['sun']
earth = eph['earth']


def comet_by_name(namepat):
    # Exact search: row = comets.loc[cometname]

    # How to search for something containing a string in pandas:
    rows = comets[comets['designation'].str.contains(namepat)]

    # Found it!
    if len(rows) == 1:
        return rows.iloc[0]

    # No match
    if len(rows) == 0:
        return None

    # Lots of possible matches, so print them but return nothing.
    # pandas iterrows() returns two things but they're both the same object,
    # not an index and an object like you might expect. So ignore r.
    for r, row in rows.iterrows():
        print(row['designation'])
    return None


def calc_comet(comet_df, thetime):
    # Generating a position.
    cometvec = sun + mpc.comet_orbit(comet_df, ts, GM_SUN)

    t = ts.utc(2020, 7, 10)
    ra, dec, distance = earth.at(t).observe(cometvec).radec()
    print("RA", ra, "DEC", dec, "distance", distance)


def Usage():
    print(f"Usage: {os.path.basename(sys.argv[0])} comet-name [date]")
    print("  comet-name may be partial, e.g. '2020 F3'.")
    print("  date can be any format that dateutil.parser can handle.")
    sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        Usage()
    if sys.argv[1] == '-h' or sys.argv[1] == '--help':
        Usage()

    if len(sys.argv) > 2:
        pdate = dateutil.parser.parse(sys.argv[2])
        if not pdate.tzinfo:
            # interpret it locally by default
            pdate = pdate.astimezone()
        # skyfield Time seems to handle aware datetimes okay,
        # so even though this says utc it will handle the given tzinfo.
        t = ts.utc(pdate)
    else:
        t = ts.now()

    comet_df = comet_by_name(sys.argv[1])

    if comet_df is not None:
        print(comet_df['designation'], "    ", t.utc_iso())
        calc_comet(comet_df, t)


