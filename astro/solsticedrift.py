#!/usr/bin/env python3

import ephem
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


date = ephem.Date(datetime.utcnow())

solstice_times = []
solstice_years = []

N_POINTS = 18

# Find the next N_POINTS summer solstices:
for i in range(N_POINTS):
    date = ephem.next_solstice(date)
    sol = date.tuple()    # (year, month, day, hour, minute, second)

    # Skip December solstices
    if sol[1] == 12:
        continue

    # Let's guess that the earliest possible solstice is midnight on June 20.
    # How much later than that is this solstice, keeping year the same??
    jun20 = ephem.Date((sol[0], 6, 20, 0, 0, 0))

    # Subtracting two ephem.Dates gives the difference in decimal days
    solstice_times.append(date - jun20)
    solstice_years.append(sol[0])


# Now plot it, specifying size in pixels.
# Unfortunately this is the size of the plot inside the window,
# not including the labels
DPI = 96
fig, ax = plt.subplots(figsize=(1000/DPI, 755/DPI), dpi=DPI)
fig.set_tight_layout(True)

ax.plot(solstice_years, solstice_times, marker='o',
        c="black", mfc='yellow', mec='red')
ax.set_title("Time of Solstice", fontsize=18, fontweight="bold")

# Y axis is fractions of days after midnight on June 20.
# Label function:
def y_label(days, tick_pos):
    if days >= 1:
        day = 21
        days -= 1
    else:
        day = 20
    hours = days * 24.
    inthours = int(hours)
    minutes = int((hours - inthours) * 60)
    return "Jun %d %02d:%02d" % (day, inthours, minutes)

ax.yaxis.set_major_formatter(FuncFormatter(y_label))

plt.show()
# plt.savefig("solsticedrift.jpg")
