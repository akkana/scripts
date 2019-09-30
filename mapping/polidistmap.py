#!/usr/bin/env python3

# https://python-visualization.github.io/folium/quickstart.html

import folium
# import shapefile    # This nonobviously comes from the pyshp module
import gdal
from json import dumps
import random
import sys


def shapefile2geojson(infile, outfile, fieldname, shapetype="Feature"):
    '''Translate a shapefile to GEOJSON.
       Similar to: ogr2ogr -t_srs EPSG:4326 -f GeoJSON file.json file.shp
    '''
    options = gdal.VectorTranslateOptions(format="GeoJSON",
                                          dstSRS="EPSG:4326")

    # gdal.VectorTranslate(dst_ds, infile, options=options)
    gdal.VectorTranslate(outfile, infile, options=options)
    print("Translated GEOJSON file", outfile)


def random_html_color():
    r = random.randint(0,256)
    g = random.randint(0,256)
    b = random.randint(0,256)
    return '#%02x%02x%02x' % (r, g, b)


def create_map(lat, lon, label, infile, fieldname):
    '''Create a map and write it to index.html
    '''
    jsonfile = infile

    m = folium.Map(location=[lat, lon], zoom_start=7)

    # Add some alternate tile layers
    folium.TileLayer('Stamen Terrain').add_to(m)
    folium.TileLayer('Stamen Toner').add_to(m)

    def style_fcn(x):
        '''The style function can key off x['properties']['NAME10']
           which will be strings like 'Senate District 42'
           but for now, let's just return random colors.
        '''
        return { 'fillColor': random_html_color() }

    def highlight_fcn(x):
        return { 'fillColor': '#ff0000' }

    gj = folium.GeoJson(jsonfile,
                        name="State %s Boundaries" % label,
                        tooltip=folium.GeoJsonTooltip(
                            fields=[fieldname],

                            # Don't include the field name in the tooltip.
                            # There doesn't seem to be a way to map to
                            # to '10' rather than ' Senate District 10';
                            # all folium allows is aliasing the field name
                            # and it will add a space even if the alias
                            # is empty.
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
    # Usage: polidistmap senate_districts.json Senate 34.588 -105.963 NAME10

    infile = sys.argv[1]
    label = sys.argv[2]
    lat = float(sys.argv[3])
    lon = float(sys.argv[4])
    fieldname = sys.argv[5]

    if not infile.lower().endswith('json'):
        jsonfile = '%s.json' % label
        shapefile2geojson(infile, jsonfile, fieldname)
        infile = jsonfile

    create_map(lat, lon, label, infile, fieldname)

