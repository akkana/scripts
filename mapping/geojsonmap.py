#!/usr/bin/env python3

# How to plot geojson shapes on top of matplotlib.
# Works with geojson polygons exported from qgis.
# Originally used "Surface Land Ownership" data from http://rgis.unm.edu/rgis6/
# which is where the 'own' codes come from.
# Hasn't been tested on other data, and obviously you'd have to change
# the colormap to reflect your own data.

import json

import matplotlib.pyplot as plt
from descartes import PolygonPatch
import matplotlib.patches as mpatches

import sys

colormap = {
    'I':   '#885500',
    'FS':  '#008800',
    'BLM': '#ff8800',
    'DOE': '#888888',
    'P':   '#ffffff',
    'NPS': '#bb00ff',
    'SP':  '#00ffff',
    'S':   '#ff0000',
    'SGF': '#88ff00',
    'OFA': '#00ffff',
    'unknown': '#000088',
}

BLACK = '#000000'

with open(sys.argv[1]) as json_file:
    json_data = json.load(json_file)

fig = plt.figure()
ax = fig.gca()

for feature in json_data['features']:
    owner = feature['properties']['own']
    if owner in colormap:
        color = colormap[owner]
    else:
        print("Unknown ownership '%s'" % owner)
        color = colormap['unknown']

    poly = feature['geometry']

    ax.add_patch(PolygonPatch(poly, fc=color, ec=BLACK, alpha=0.5, zorder=2 ))

# create legend
legend_patches = []
for c in colormap:
    legend_patches.append(mpatches.Patch(color=colormap[c], label=c))
plt.legend(handles=legend_patches, title='Ownership')

plt.tight_layout(pad=0, w_pad=0, h_pad=0)
ax.axis('scaled')
plt.show()

