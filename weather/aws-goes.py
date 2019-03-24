#!/usr/bin/env python3

# An example of how to fetch NOAA GOES-16 data from AWS and plot it on a map.

import matplotlib.pyplot as plt
from netCDF4 import Dataset
from mpl_toolkits.basemap import Basemap
import numpy as np
import requests
import os
import sys
from bs4 import BeautifulSoup

baseurl = 'https://s3.amazonaws.com/noaa-goes16/'
localindex = 'noaa-goes-16.xml'

def analyze_dataset(dataset):
    '''Print out what's in the dataset, to figure out what's plottable.
    '''
    print("variables:", '\n'.join(dataset.variables.keys()))

    for var in dataset.variables:
        print("\n=======", var)
        try:
            print(dataset[var].long_name)
            print(dataset[var].units)
            print(dataset[var].shape)
        except AttributeError:
            print("Not all attributes found")
            print(dataset[var])


def plot_file(filename):
    # Open the file using the NetCDF4 library
    nc = Dataset(filename)

    # analyze_dataset(nc)

    latlon = nc.variables['geospatial_lat_lon_extent']
    # print('geospatial_lat_lon_extent:', latlon)

    # Original example uses Brightness Temperature values, 'CMI'
    # But that's not in our dataset.
    whichvar = 'Rad'
    data = nc.variables[whichvar][:]
    prettyname = nc.variables[whichvar].long_name

    # Show it without basemap:
    # plt.imshow(data, cmap='Greys')
    # plt.show()

    # Create the basemap reference for the Satellite Projection
    bmap = Basemap(projection='geos',

                   # Extents
                   llcrnrlon=latlon.geospatial_westbound_longitude,
                   llcrnrlat=latlon.geospatial_southbound_latitude,
                   urcrnrlon=latlon.geospatial_eastbound_longitude,
                   urcrnrlat=latlon.geospatial_northbound_latitude,

                   # Should these be nadir, or center?
                   lon_0=latlon.geospatial_lon_nadir,
                   lat_0=latlon.geospatial_lat_nadir,
                   satellite_height=35786023.0, ellps='GRS80')

    # Plot GOES-16 Channel using 170 and 378 as the temperature thresholds
    bmap.imshow(data, origin='upper', cmap='Greys')

    # Draw the coastlines, countries, parallels and meridians
    bmap.drawcoastlines(linewidth=0.3, linestyle='solid', color='blue')
    bmap.drawcountries(linewidth=0.3, linestyle='solid', color='blue')

    # These don't seem to do anything
    bmap.drawparallels(np.arange(-90.0, 90.0, 10.0),
                       linewidth=0.1, color='yellow')
    bmap.drawmeridians(np.arange(0.0, 360.0, 10.0),
                       linewidth=0.1, color='yellow')

    # Insert the legend
    bmap.colorbar(location='bottom', label=prettyname)

    # Show the plot
    plt.show()


def get_xml_index():
    '''Return the XML AWS index, fetching it if necessary, caching locally.
    '''
    if os.path.exists(localindex):
        with open(localindex) as fp:
            return fp.read()

    print("Fetching index")
    r = requests.get(baseurl)
    xml = r.text
    with open(localindex, 'w') as fp:
        fp.write(xml)
    return xml


if __name__ == '__main__':
    # If there are files specified, use them:
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            plot_file(f)
        sys.exit(0)

    # If no files specified, download files based on the XML index.
    xml = get_xml_index()

    soup = BeautifulSoup(xml, 'lxml')
    for key in soup.find_all('key'):
        url = baseurl + key.text
        filename = key.text.replace('/', '_')
        if not os.path.exists(filename):
            with open(filename, 'wb') as fp:
                print("Fetching", url, "...", end='')
                r = requests.get(url)
                print(r.status_code)
                if r.status_code == 200:
                    print("Writing to", filename)
                    sys.stdout.flush()
                    fp.write(r.content)
                    print("Wrote", filename)
                else:
                    print("Couldn't fetch", key.text)

        sys.stdout.flush()
        sys.stderr.flush()
        if os.stat(filename).st_size > 0:
            if filename != 'ABI-L1b-RadC_2000_001_12_OR_ABI-L1b-RadC-M3C01_G16_s20000011200000_e20000011200000_c20170671748180.nc':
                plot_file(filename)
        else:
            print(filename, "is zero size")


