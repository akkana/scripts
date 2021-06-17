#!/usr/bin/env python3

# Plot summer solstice times on successive years.
# To save the plot to a file, run it with desired filename as argument.
# Copyright 2021 by Akkana Peck. Share and enjoy under the GPLv2 or later.

import ephem
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FixedLocator
from matplotlib import rcParams
import sys


date = datetime.utcnow()

solstice_times = []
solstice_years = []

N_POINTS = 14

orig_year = date.year

# Find the next N_POINTS summer solstices:
for i in range(N_POINTS):
    date += timedelta(days=1)
    ephemdate = ephem.Date(date)
    ephemdate = ephem.next_solstice(date)
    if ephemdate.tuple()[1] == 12:
        ephemdate = ephem.next_solstice(ephemdate)

    # Convert to datetime and make it aware that timezone is utc
    date = ephemdate.datetime().replace(tzinfo=timezone.utc)
    # Convert to an aware datetime in the local timezone
    date = date.astimezone()

    solstice_times.append(date.replace(year=orig_year))

    solstice_years.append(date.year)

# Now plot it, specifying size in pixels.
# Unfortunately this is the size of the plot inside the window,
# not including the labels
DPI = 96
fig, ax = plt.subplots(figsize=(1000/DPI, 755/DPI), dpi=DPI)
fig.set_tight_layout(True)

ax.plot(solstice_years, solstice_times, marker='o',
        c="black", mfc='yellow', mec='red')
ax.set_title("Time of Solstice", fontsize=18, fontweight="bold")

# ax.yaxis.set_major_formatter(FuncFormatter(y_label))
# Stupid matplotlib ignores the timezone in datetimes and converts to UTC
# unless you explicitly pass the name of the timezone.
rcParams['timezone'] = date.tzname()
myFmt = mdates.DateFormatter("%b %d %H:%M")
ax.yaxis.set_major_formatter(myFmt)

# This only shows every other year:
# ax.xaxis.set_major_locator(MaxNLocator(integer=True))
# This shows all of them:
ax.xaxis.set_major_locator(FixedLocator([2021+i for i in range(N_POINTS)]))

plt.grid(True)

# You can either show it interactively, or save it, not both.
if len(sys.argv) <= 1:
    plt.show()

else:
    plt.savefig(sys.argv[1], dpi=DPI)
    print("Saved as", sys.argv[1])
