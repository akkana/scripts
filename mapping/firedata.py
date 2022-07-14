#!/usr/bin/env python3

import requests
import csv
import time
import subprocess
import sys, os


# All of NM state
# master_bbox = ( -109, 30.949, -104, 37.3 )
# Jemez and Sangres
master_bbox = ( -107, 35.15, -104.55, 36.6 )

datadir = os.path.expanduser("~/Data/cerropelado")

# The two satellite datasets to pull, MODIS and VIIRS.
# NASA says in https://www.earthdata.nasa.gov/resource-spotlight/wildfires :
# "Active fire/hotspot data acquired by instruments aboard geostationary
# satellites will be added to FIRMS later in 2022."
# so keep an eye on FIRMS; it may be worth adding other FIRMS URLs.
sat_urls = ( 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_USA_contiguous_and_Hawaii_24h.csv',
             'https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv'
            )
sat_files = []   # Will be filled in later

# The fire extent boundary
boundary_url = 'https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/Fire_History_Perimeters_Public/FeatureServer/0/query?where=1%%3D1&outFields=*&geometry=%f%%2C%f%%2C%f%%2C%f&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outSR=4326&f=json' % master_bbox


GPX_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.0" creator="firedata.py"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns="http://www.topografix.com/GPX/1/0"
 xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">"""
GPX_FOOTER = "</gpx>"


def in_bbox(lat, lon, bbox):
    return lat >= bbox[1] and lat <= bbox[3] \
        and lon >= bbox[0] and lon <= bbox[2]


# Fetch the two CSV files and throw out anything outside the bbox
datestr = time.strftime("%Y-%m-%d-%a")
for satset in sat_urls:
    base = os.path.basename(satset).split('.')[0] + "-" + datestr
    csvfile = os.path.join(datadir, base + ".csv")
    gpxfile = os.path.join(datadir, base + ".gpx")

    # If it hasn't already been fetched, fetch it now.
    if not os.path.exists(csvfile):
        print("Downloading", satset, "to", csvfile)
        csvdata = requests.get(satset).text
        with open(csvfile, 'w') as ofp:
            ofp.write(csvdata)
            print("Saved original CSV as", csvfile)
        csvdata = None    # free up some memory
    else:
        print(csvfile, "already exists")

    with open(csvfile) as infp:
        reader = csv.DictReader(infp)
        with open(gpxfile, "w") as ofp:
            ofp.write(GPX_HEADER)
            for row in reader:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                if in_bbox(lat, lon, master_bbox):
                    print(f"""<wpt lat="{lat}" lon="{lon}"></wpt>""", file=ofp)
            ofp.write(GPX_FOOTER)
            print("Wrote", gpxfile)

    sat_files.append(gpxfile)

# Now fetch the latest fire boundary, in the silly esri json format
boundarybase = "boundary-" + datestr
boundary_esrifile = os.path.join(datadir, boundarybase + ".esrijson")
boundary_geojson = os.path.join(datadir, boundarybase + ".geojson")
if not os.path.exists(boundary_geojson):
    if not os.path.exists(boundary_esrifile):
        with open(boundary_esrifile, "w") as ofp:
            print("Fetching new boundary file")
            boundary_json = requests.get(boundary_url).text
            ofp.write(boundary_json)
    else:
        print(boundary_esrifile, "already exists")

    print("Converting ESRIjson to GeoJSON")
    rv = subprocess.call(["ogr2ogr", "-f", "GeoJSON",
                          boundary_geojson,
                          boundary_esrifile])
    if rv != 0:
        print("Conversion failed")
        sys.exit(rv)
else:
    print(boundary_geojson, "already exists")

print("All done! Try running:")
print("pytopo %s %s -k poly_IncidentName %s"
      % (os.path.join(datadir, "go-lines.gpx"),
         ' '.join(sat_files),
         boundary_geojson))


if __name__ == '__main__':
    pass

