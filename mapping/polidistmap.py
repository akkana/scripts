#!/usr/bin/env python3

# https://python-visualization.github.io/folium/quickstart.html

import folium
import shapefile    # This nonobviously comes from the pyshp module
from json import dumps
import random
import sys

# Note: to create geojson from shapefiles, use
#   ogr2ogr -t_srs EPSG:4326 -f GeoJSON file.json file.shp

def random_html_color():
    r = random.randint(0,256)
    g = random.randint(0,256)
    b = random.randint(0,256)
    return '#%02x%02x%02x' % (r, g, b)

def create_map(lat, lon, chamber, jsonfile):
    '''Create a map and write it to index.html
    '''
    m = folium.Map(location=[lat, lon],
                   tiles='Stamen Terrain',
                   zoom_start=7)

    def style_fcn(x):
        '''The style function can key off x['properties']['NAME10']
           which will be strings like 'Senate District 42'
           but for now, let's just return random colors.
        '''
        return { 'fillColor': random_html_color() }

    def highlight_fcn(x):
        return { 'fillColor': '#ff0000' }

    gj = folium.GeoJson(jsonfile,
                        name="State %s Boundaries" % chamber,
                        tooltip=folium.GeoJsonTooltip(
                            fields=['NAME10'],

                            # Don't show the "NAME10" in the tooltip.
                            # There doesn't seem to be a
                            # way to map the actual content
                            # to show '10' rather than ' Senate District 10'
                            aliases=[''],

                            # Optionally can pass a style
                            # style="font-family: serif;",
                        ),
                        style_function=style_fcn,
                        highlight_function=highlight_fcn)

    # Here's how to add a popup to the whole GeoJSON object.
    # gj.add_child(folium.Popup('outline Popup on GeoJSON'))
    # But it doesn't help in adding a popup that shows the current polygon.
    # The only way seems to be to add each polygon as a separate feature:
    # https://stackoverflow.com/a/54738210
    # There may eventually be a way to do this:
    # https://github.com/python-visualization/folium/issues/802

    gj.add_to(m)

    folium.LayerControl().add_to(m)

    m.save('index.html')
    print("Saved to index.html")


if __name__ == '__main__':
    # Usage: polidistmap senate_districts.json Senate 34.588 -105.963

    jsonfile = sys.argv[1]
    chamber = sys.argv[2]
    lat = float(sys.argv[3])
    lon = float(sys.argv[4])

    create_map(lat, lon, chamber, jsonfile)

