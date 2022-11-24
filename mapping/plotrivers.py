#!/usr/bin/env python3

"""
This is an attempt to get the slightly out of date
https://towardsdatascience.com/creating-beautiful-river-maps-with-python-37c9b5f5b74c
to work with current datasets, and to show North America instead of Africa.
Data:
http://gaia.geosci.unc.edu/rivers/
    Download BOTH:
        North America, namerica.zip
        Central America, camerica.zip
    You need both because the North America dataset
    unaccountably omits the entire Rio Grande basin.
https://www.hydrosheds.org/products/hydrobasins
    Download the North America "Customized (with lakes)",
    hybas_na_lev01-12_v1c.zip
https://www.naturalearthdata.com/downloads/
    In 1:10m Physical Vectors, download
        lakes (ne_10m_lakes.zip)
        lakes, North America Supplement (ne_10m_lakes_north_america.zip)
    In 1:10m Cultural Vectors, download
        countries (ne_10m_admin_0_countries.zip)
"""


import os

# Debian bug #1013186: pyproj can't find its own proj dir
# if in a virtualenv with --system-site-packages.
# The maintainer has said he's not interested in changes to
# make it easier to use virtualenvs.
# So to avoid a warning, it has to be set via environment variable
# before importing pyproj (which is imported by importing geopandas).
os.environ['PROJ_LIB'] = '/usr/share/proj/'

import geopandas as gpd

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors

from datetime import datetime


DATADIR = os.path.expanduser('~/Data/Rivers')

START_TIME = datetime.now()
SECTION_START_TIME = START_TIME


# The tutorial runs through lots of preliminary plots.
# That slows things down if you just want to generate the final plot.
SHOW_EVERYTHING = False

colours_i_like = ['#875692', '#008856',  '#0067A5', '#BE0032',
                  '#222222', '#F38400', 'blue', '#604E97',
                  '#E68FAC', '#F3C300', '#B3446C', '#C2B280',
                  '#F6A600', '#882D17', '#E25822', '#8DB600',
                  '#F99379',  '#DCD300', '#F3C300', '#E68FAC', '#C2B280',
                  # colors I don't actually like:
                   '#848482', '#F3C300'
                  ]

# Show the color swatches first, before reading any data
if SHOW_EVERYTHING:
    cell_width = 212
    cell_height = 22
    swatch_width = 48
    margin = 12
    topmargin = 40

    n = len(colours_i_like)
    ncols = 1
    nrows = len(colours_i_like)
    width = cell_width * 4 + 2 * margin
    height = cell_height * nrows + margin + topmargin
    dpi = 72

    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    fig.subplots_adjust(margin/width, margin/height,
                        (width-margin)/width, (height-topmargin)/height)
    ax.set_xlim(0, cell_width * 4)
    ax.set_ylim(cell_height * (nrows-0.5), -cell_height/2.)
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.set_axis_off()
    ax.set_title("Basin Colors", fontsize=24, loc="left", pad=10)

    # Again, the tutorial used MAJ_NAME but it's not a field in the data.
    # The tutorial used basin names when showing the swatches,
    # but the actual data no longer has names for the basins, alas.
    for i, color in enumerate(colours_i_like):
        row = i % nrows
        col = i // nrows
        y = row * cell_height

        swatch_start_x = cell_width * col
        text_pos_x = cell_width * col + swatch_width + 7

        ax.text(text_pos_x, y, (color), fontsize=14,
                horizontalalignment='left',
                verticalalignment='center')

        ax.add_patch(
            Rectangle(xy=(swatch_start_x, y-9), width=swatch_width,
                      height=18, facecolor=color, edgecolor='0.7')
        )
    plt.show()


now = datetime.now()
print(f"Calculated color swatches ({now - SECTION_START_TIME})")
SECTION_START_TIME = now


# Read country and continent shapes
country_shapefiles = gpd.read_file(
    os.path.join(DATADIR, "10m_cultural/ne_10m_admin_0_countries.shp"))
north_america = country_shapefiles.loc[country_shapefiles['CONTINENT']
                                       == 'North America']
north_america = north_america[['geometry']]

# Read the rivers. The North American rivers dataset doesn't include
# the Rio Grande, which unaccountably is in the Central American file
# instead. And oh, joy, the two datasets have a completely different
# set of columns. All we really need for this demo is the geometry.
# The ID, called # ARCID in NA and a_ARCID in CA, isn't unique anyway
# (e.g. both datasets have something with ID 391, and they're different).
# So the ARCID column is omitted, but I left the commented lines in
# as a reminder for how to rename a column.
na_rivers = gpd.read_file(os.path.join(DATADIR, "unc-rivers/narivs.shp"))
# print("Initially, na_rivers has columns", na_rivers.columns)
ca_rivers = gpd.read_file(os.path.join(DATADIR, "unc-rivers/carivs.shp"))
# print("Initially, ca_rivers has columns", ca_rivers.columns)
ca_rivers.rename(columns={'a_DEPTH': 'DEPTH', 'a_WIDTH': 'WIDTH'},
                 inplace=True)

# limit to columns of interest
na_rivers = na_rivers[['geometry', 'DEPTH', 'WIDTH']]
ca_rivers = ca_rivers[['geometry', 'DEPTH', 'WIDTH']]

# How to rename a column. But these aren't unique identifiers
# in the merged dataset.
# ca_rivers.rename(columns={'a_ARCID': 'ARCID'}, inplace=True)

# Merge the two datasets
na_rivers = pd.concat([na_rivers, ca_rivers])

# done with ca_rivers, free up memory
ca_rivers = None

now = datetime.now()
print(f"Merged North and Central American Rivers ({now - SECTION_START_TIME})")
SECTION_START_TIME = now


# Read in the lakes. Weirdly, ne_10m_lakes.shp and ne_10m_lakes_north_america
# show a completely different list of lakes; the latter has bigger lakes,
# like Tahoe and the Great Salt Lake, while the former has smaller ones
# like Navajo Lake. Neither one shows most lakes in NM, like Elephant
# Butte, Heron/El Vado or Abiquui. Sigh.
smalllakes = gpd.read_file(os.path.join(DATADIR, "lakes/ne_10m_lakes.shp"))
biglakes = gpd.read_file(os.path.join(DATADIR,
                                      "lakes/ne_10m_lakes_north_america.shp"))

# limit columns
smalllakes = smalllakes[['name', 'geometry']]
biglakes = biglakes[['name', 'geometry']]

na_lakes = pd.concat([biglakes, smalllakes])
biglakes = None
smalllakes = None

# Some of the rivers in the database are actually underwater in lakes.
# Do a spatial join that excludes rivers that intersect with lakes,
# in order to show lakes better.

# This probably makes no difference since the rivers dataset are
# the union of north america and central america datasets,
# while north_america
na_lakes = gpd.sjoin(na_lakes, north_america, predicate='intersects')
# The sjoin added a ton of new columns to na_lakes, which now has:
# name', 'geometry', 'index_right', 'featurecla', 'scalerank',
# 'LABELRANK', 'SOVEREIGNT', 'SOV_A3', 'ADM0_DIF', 'LEVEL',
#   ...
# 'FCLASS_VN', 'FCLASS_TR', 'FCLASS_ID', 'FCLASS_PL', 'FCLASS_GR',
# 'FCLASS_IT', 'FCLASS_NL', 'FCLASS_SE', 'FCLASS_BD', 'FCLASS_UA'
# The index_left, index_right make the excluded_rivers = sjoin line die.
# So remove all extra columns.
na_lakes = na_lakes[['name', 'geometry']]

# This doesn't actually restrict it any further:
na_lakes = na_lakes.loc[na_lakes.index.isin(na_lakes.index.tolist())]

excluded_rivers = gpd.sjoin(na_rivers, na_lakes, predicate='within')
na_rivers = na_rivers.loc[~na_rivers.index.isin(excluded_rivers.index.tolist())]

now = datetime.now()
print(f"Added lakes ({now - SECTION_START_TIME})")

if SHOW_EVERYTHING:
    # Take a look at what we have so far.
    fig, ax = plt.subplots(facecolor='#FCF6F5FF')
    fig.set_size_inches(7, 5)
    # ax.set_xlim([0, enddate])
    # ax.set_ylim([0, data[-1]])

    # XXX This plots quite small in a big window.
    # Try to make it come closer to filling the window:
    plt.margins(x=0)
    fig.tight_layout(pad=0, w_pad=0, h_pad=0)

    na_rivers.plot(ax=ax, color='blue', lw=0.1)
    # na_lakes.plot(ax=ax, color='purple', alpha=1)
    na_lakes.plot(ax=ax, color="none", facecolor="none",
                  edgecolor='purple', alpha=1)

    ax.axis('off')

    plt.show()

SECTION_START_TIME = now

'''
#
# Try to show all the streams in the dataset that are actually
# under a lake.
#

one_lake = na_lakes.loc[na_lakes['name'] == 'Lake Tahoe']
print("one_lake", one_lake)

# This part of the tutorial doesn't work: there are no underwater_streams
# in the north american dataset the way the tutorial showed in Africa.
underwater_streams = gpd.sjoin(na_rivers, one_lake, predicate='within')
print("underwater_streams", underwater_streams)

fig, ax = plt.subplots(facecolor='#FCF6F5FF')
fig.set_size_inches(5, 7)

one_lake.plot(ax=ax, color='black', alpha=0.1)
underwater_streams.plot(ax=ax, color='blue', lw=0.4, alpha=1)

ax.axis('off')

plt.show()
'''

#
# Now use the hydrobasins from https://www.hydrosheds.org/products/hydrobasins
#

# This part doesn't work because the data doesn't have the expected MAJ_NAME.
# If I change MAJ_NAME to HYBAS_ID, then it fails because it has the
# wrong number of colors. Very brittle code.
# I'd like a way to plot it with random colors.
basins = gpd.read_file(os.path.join(DATADIR,
                                    "hydrobasins/hybas_na_lev02_v1c.shp"))

# Assign colors from the colour list to basins
colors_df = pd.DataFrame({'basin': basins.HYBAS_ID.unique().tolist(),
                          'colors': colours_i_like[:8]})

now = datetime.now()
print(f"Read in the basins ({now - SECTION_START_TIME})")

#
# Merge the basins GeoDataFrame with the colours df,
# with the basins polygons being coloured by the predefined colours.
#
basins = pd.merge(basins, colors_df, left_on='HYBAS_ID',
                  right_on='basin', how='left')

if SHOW_EVERYTHING:
    fig, ax = plt.subplots(facecolor='#FCF6F5FF')
    # XXX geopandas/plotting.py:656: UserWarning: Only specify one of 'column' or 'color'. Using 'color'.
    # basins.plot(ax=ax, column='HYBAS_ID', edgecolor='face', color=basins['colors'])
    # basins.plot(ax=ax, column='HYBAS_ID', color=basins['colors'])
    basins.plot(ax=ax, color=basins['colors'])
    ax.axis('off')
    plt.show()

SECTION_START_TIME = now


#
# Now match the rivers with the basins.
# This takes FOREVER -- like an hour and a half or more on a fast machine.
#
rivers_basins = gpd.sjoin(na_rivers, basins, predicate='intersects')

now = datetime.now()
print("Calculated intersection of rivers and basins "
      f"({now - SECTION_START_TIME})")


if SHOW_EVERYTHING:
    fig, ax = plt.subplots(facecolor='#FCF6F5FF')
    fig.set_size_inches(7, 5)

    # Try again to make the size reasonable
    plt.margins(x=0)
    fig.tight_layout(pad=0, w_pad=0, h_pad=0)

    # The plot comes out faded, washed out compared to the tutorial,
    # and you really can't see any river detail.
    rivers_basins.plot(ax=ax, edgecolor='face',
                       color=rivers_basins['colors'], lw=0.1)
    na_lakes.plot(ax=ax, color='#FCF6F5FF')

    # logo = plt.imread('../../Branding/globe.png')
    # newax = fig.add_axes([0.83, 0.62, 0.1, 0.1], anchor='NE', zorder=-1)
    # newax.imshow(logo)
    # newax.axis('off')
    txt = ax.text(0.02, 0.03, "North American Rivers",
                  size=6,
                  color='black',
                  transform = ax.transAxes,
                  fontfamily='fantasy')

    ax.axis('off')
    plt.show()

SECTION_START_TIME = now


#
# Make a plot with the river linewidths scaled according to
# different aspects of river size.
#

def scale_lw(df: gpd.GeoDataFrame, column_name: str,
             min_value: float = 0.005, max_value: float = 0.6):
    leftSpan = np.amax(df[column_name]) - np.amin(df[column_name])
    rightSpan = 0.6 - 0.005
    valueScaled = (df[column_name] - np.amin(df[column_name])) / leftSpan
    df[f'LW_{column_name}'] = 0.005 + (valueScaled * rightSpan)
    return df

# We'll use depth for the line width scaling:
# it gives the best result.
rivers_basins = scale_lw(rivers_basins, 'DEPTH',
                         min_value=0.005, max_value=0.6)


now = datetime.now()
print(f"Scaled line widths ({now - SECTION_START_TIME})")

if SHOW_EVERYTHING:
    rivers_basins = scale_lw(rivers_basins, 'WIDTH',
                             min_value=0.005, max_value=0.6)
    # CA river data doesn't have DISCHARGE
    # rivers_basins = scale_lw(rivers_basins, 'DISCHARGE',
    #                          min_value=0.005, max_value=0.6)

    fig = plt.figure(facecolor='#FCF6F5FF')
    fig.set_size_inches(15, 7)

    # ax1 = plt.subplot(1,3,1)
    # rivers_basins.plot(ax=ax1, color='blue', lw=rivers_basins['LW_DISCHARGE'])
    # na_lakes.plot(ax=ax1, color='#FCF6F5FF')
    # ax1.set_title("Discharge", fontfamily='fantasy')
    # ax1.axis('off')

    ax2 = plt.subplot(1, 2, 1)
    rivers_basins.plot(ax=ax2, color='blue', lw=rivers_basins['LW_WIDTH'])
    na_lakes.plot(ax=ax2, color='#FCF6F5FF')
    ax2.set_title("Width", fontfamily='fantasy')
    ax2.axis('off')

    ax3 = plt.subplot(1, 2, 2)
    rivers_basins.plot(ax=ax3, color='blue', lw=rivers_basins['LW_DEPTH'])
    na_lakes.plot(ax=ax3, color='#FCF6F5FF')
    ax3.set_title("Depth", fontfamily='fantasy')
    ax3.axis('off')

    # Try again to make the size reasonable
    plt.margins(x=0)
    fig.tight_layout(pad=0, w_pad=0, h_pad=0)

    plt.show()


# Answer: Depth is better, shows more detail, darker.
# So use that on the large plot.

#
# Larger plot, rivers all the same color
#

if SHOW_EVERYTHING:
    fig, ax = plt.subplots(facecolor='#FCF6F5FF')
    fig.set_size_inches(7, 5)

    # Try again to make the size reasonable
    plt.margins(x=0)
    fig.tight_layout(pad=0, w_pad=0, h_pad=0)

    rivers_basins.plot(ax=ax, edgecolor='face', color='blue',
                       lw=rivers_basins['LW_DEPTH'])
    na_lakes.plot(ax=ax, color='#FCF6F5FF')

    # newax = fig.add_axes([0.83, 0.62, 0.1, 0.1], anchor='NE', zorder=-1)
    # newax.imshow(logo)
    # newax.axis('off')
    txt = ax.text(0.02, 0.03, "North American Rivers",
                  size=6,
                  color='grey',
                  transform = ax.transAxes,
                  fontfamily='fantasy')

    ax.axis('off')
    plt.show()

SECTION_START_TIME = now


#
# The final plot, colored by basin
#

now = datetime.now()
print(f"Ready to make final plot ({now - SECTION_START_TIME})")
SECTION_START_TIME = now

fig, ax = plt.subplots(facecolor='white')
fig.set_size_inches(7, 5)

# Try again to make the size reasonable. It doesn't succeed,
# but at least it makes things a little better.
plt.margins(x=0)
fig.tight_layout(pad=0, w_pad=0, h_pad=0)

rivers_basins.plot(ax=ax, edgecolor='face', color=rivers_basins['colors'],
                   lw=rivers_basins['LW_DEPTH'])
na_lakes.plot(ax=ax, color='#FCF6F5FF')

# newax = fig.add_axes([0.83, 0.62, 0.1, 0.1], anchor='NE', zorder=-1)
# newax.imshow(logo)
# newax.axis('off')
txt = ax.text(0.02, 0.03, "North American Rivers",
              size=6,
              color='grey',
              transform = ax.transAxes,
              fontfamily='fantasy')

ax.axis('off')

now = datetime.now()
print(f"Final plot is ready ({now - SECTION_START_TIME})")
SECTION_START_TIME = now
print(f"Total time was {now - START_TIME}")

plt.show()

# Running the above takes several hours, which makes it hard
# to fiddle with plotting and try to get matplotlib to do
# something sensible. So save what we've calculated so far.
print("fields in rivers_basins:", rivers_basins.columns)
'''
Calculated color swatches (0:00:00.000005)
Merged North and Central American Rivers (0:00:27.564679)
Added lakes (0:00:31.760115)
Read in the basins (0:00:00.358680)
Calculated intersection of rivers and basins (0:38:01.949588)
Scaled line widths (0:00:00.008554)
Ready to make final plot (0:00:00.000040)
Final plot is ready (0:00:44.952849)
Total time was 0:39:46.594510
fields in rivers_basins: Index(['geometry', 'DEPTH', 'WIDTH', 'index_right', 'HYBAS_ID', 'NEXT_DOWN',
       'NEXT_SINK', 'MAIN_BAS', 'DIST_SINK', 'DIST_MAIN', 'SUB_AREA',
       'UP_AREA', 'PFAF_ID', 'ENDO', 'COAST', 'ORDER', 'SORT', 'basin',
       'colors', 'LW_DEPTH'],
      dtype='object')
'''
# rivers_basins = rivers_basins[[
# na_rivers = na_rivers[['geometry', 'DEPTH', 'WIDTH']]
