#!/usr/bin/env python

# Plot US airline routes on a background with state boundaries.

# airline and route data: https://openflights.org/data.html
# us-states.json: there are various versions floating around, e.g.
#   https://github.com/PublicaMundi/MappingAPI/blob/master/data/geojson/us-states.json
#   https://raw.githubusercontent.com/giswqs/geemap/master/examples/data/us-states.json
# code help:
#     https://towardsdatascience.com/mapping-the-worlds-flight-paths-with-python-232b9f7271e5
#     https://coderzcolumn.com/tutorials/data-science/plotting-static-maps-with-geopandas-working-with-geospatial-data

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString
import cartopy.crs as ccrs
import os


DATADIR = os.path.expanduser("~/Data/geopandas")


# When debugging, this is helpful to show all columns:
pd.set_option('display.max_columns', None)
# otherwise you can use print(pandas_expression).to_string()) every time.

# Also, make pandas check the actual width of the terminal:
pd.options.display.width = 0

airports = pd.read_csv(os.path.join(DATADIR, "airports.dat"), delimiter=',',
                       names=['id', 'name', 'city', 'country', 'iata',
                              'icao', 'lat', 'long', 'altitude', 'timezone',
                              'dst', 'tz', 'type', 'source'])

# Limit to airports in the lower 48
airports = airports[(airports["country"] == "United States") &
                    (airports["tz"] != "America/Anchorage") &
                    (airports["tz"] != "Pacific/Honolulu")
                    ]

routes = pd.read_csv(os.path.join(DATADIR, "routes.dat"), delimiter=',',
                     names=['airline', 'id', 'source_airport',
                            'source_airport_id',
                            'destination_airport', 'destination_airport_id',
                            'codeshare', 'stops', 'equipment'])

# Now limit it to routes where routes["source_airport"] and
# routes["destination_airport"] are both in airports["iata"]
routes = routes.loc[routes.source_airport.isin(airports.iata) &
                    routes.destination_airport.isin(airports.iata)]

# Duplicate the source dataframe to represent destinations
source_airports = airports[['name', 'iata', 'icao', 'lat', 'long']]
destination_airports = source_airports.copy()

# Merge the source DataFrame with the routes using the routes source iata code.
source_airports.columns = [str(col) + '_source'
                           for col in source_airports.columns]

# Same for destinations
destination_airports.columns = [str(col) + '_destination'
                                for col in destination_airports.columns]

# Use the lat/lon values of the source and destinations airports
# which are now merged into the routes DataFrame
# to create a LineString representing that route.
routes = routes[['source_airport', 'destination_airport']]
routes = pd.merge(routes, source_airports,
                  left_on='source_airport', right_on='iata_source')
routes = pd.merge(routes, destination_airports,
                  left_on='destination_airport', right_on='iata_destination')

geometry = [LineString([[routes.iloc[i]['long_source'],
                         routes.iloc[i]['lat_source']],
                        [routes.iloc[i]['long_destination'],
                         routes.iloc[i]['lat_destination']]])
            for i in range(routes.shape[0])]
routes = gpd.GeoDataFrame(routes, geometry=geometry, crs='EPSG:4326')
# routes = gpd.GeoDataFrame(routes, geometry=geometry)


# Background map of the states
usa = gpd.read_file(os.path.join(DATADIR, "us-states.json"))

# Limit to the lower 48:
usa = usa[(usa.name != 'Alaska') &
          (usa.name != 'Hawaii') &
          (usa.name != 'Puerto Rico')]

#
# Finally, it's time to plot
#

fig = plt.figure(facecolor='white')
ax = plt.axes(projection=ccrs.Mercator())
fig.set_size_inches(12, 6)
# ax.patch.set_facecolor('white')

basemap = usa.plot(ax=ax, color="ivory", edgecolor="black")

routes.plot(ax=basemap,

            # XXX Geodetic transform to get great circle lines doesn't
            # work, maybe because it conflicts with the Mercator
            # projection already specified.
            # I haven't found a solution to that yet.
            # transform=ccrs.Geodetic(),

            # The docs say this should work, but it gives:
            # IndexError: index 1 is out of bounds for axis 0 with size 1
            # style_kwds={"linewidth": 1.5})

            color='red', alpha=0.01)

plt.tight_layout()

plt.show()
