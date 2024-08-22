#!/usr/bin/env python3

# Map features from the USGS National Map's
# Geographic Names Information System (GNIS)
# which is stored in Text/DomesticNames_{STATE_ABBREV}.txt
# as CSV with a | separator.
# Get the GNIS from the National Map Downloader,
#   https://apps.nationalmap.gov/downloader/

import folium
from folium.features import DivIcon

import csv
from sys import argv, stdout

spaces = ' ' * 60


# Pare down to a smaller set
MIN_LON = -106.4336827
MAX_LON = -106.1411717
MIN_LAT = 35.7466669
MAX_LAT = 35.9527426

numinbounds = 0
def WITHIN_BOUNDS(lon, lat):
    global numinbounds
    if lon < MIN_LON or lon > MAX_LON:
        return False
    if lat < MIN_LAT or lat > MAX_LAT:
        return False
    numinbounds += 1
    return True


def map_features(filename, featureclass):
    m = folium.Map(control_scale=True)
    featureclass = featureclass.lower()

    numfeatures = 0
    with open(filename) as csvfp:
        reader = csv.DictReader(csvfp, delimiter="|")
        for row in reader:
            if row['feature_class'].lower() != featureclass:
                continue
            # print(row)

            name = row['feature_name']
            mouth_lat = float(row['prim_lat_dec'])
            mouth_lon = float(row['prim_long_dec'])
            source_lat = float(row['source_lat_dec'])
            source_lon = float(row['source_long_dec'])

            if not WITHIN_BOUNDS(mouth_lon, mouth_lat):
                continue
            if not WITHIN_BOUNDS(source_lon, source_lat):
                continue

            if mouth_lat and mouth_lon:
                folium.Marker([mouth_lat, mouth_lon], tooltip=name,
                              icon=DivIcon(icon_size=(150,36),
                                           icon_anchor=(0,0),
                                           html='<div style="font-size: 10pt; color: purple">%s</div>' % name
                              )).add_to(m)
            if source_lat and source_lon:
                folium.Marker([source_lat, source_lon], tooltip=name,
                              icon=DivIcon(icon_size=(150,36),
                                           icon_anchor=(0,0),
                                           html='<div style="font-size: 10pt; color: blue">%s</div>' % name
                              )).add_to(m)
                # There doesn't seem to be a way to have a folium marker
                # that displays both text AND an icon. If you want the
                # icon in addition to the text, add a separate marker
                # (which slows down the map considerably).
                # folium.Marker([mouth_lat, mouth_lon], tooltip=name,
                #               ).add_to(m)

            # If it's an extended feature, like a valley, it will
            # have both "prim" coordinates (the mouth of a valley)
            # and "source" (the source). Draw a line between them.
            if mouth_lat and mouth_lon and source_lat and source_lon:
                folium.PolyLine([ [ source_lat, source_lon ],
                                  [ mouth_lat, mouth_lon ] ],
                                tooltip=name,
                                color="#0af", weight=15, opacity=.3
                                ).add_to(m)

            numfeatures += 1
            print(f"\r{spaces}\r\r{numfeatures}: {name}", end='')
            stdout.flush()

    print()

    m.fit_bounds(m.get_bounds())
    outfile = f"{featureclass}.html"
    m.save(outfile)
    print("Saved to", outfile)


if __name__ == '__main__':
    if len(argv) != 3:
        print("Usage: map_named_features demfile featureclass")
        exit(1)
    map_features(argv[1], argv[2])

