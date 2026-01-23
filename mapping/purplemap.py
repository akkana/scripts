#!/usr/bin/env python3

import csv
import json
import re
import zipfile
import folium
import os, sys


def create_geojson(precinctfile, datadir, statename, outfilename):
    """Create a GeoJSON file for a single state"""
    with open(precinctfile) as fp:
        precinctjson = json.load(fp)

    # TEMPORARY to make it easier to inspect the file, remove the GIS
    # for feature in precinctjson['features']:
    #     del feature['geometry']

    zipfilename = os.path.join(datadir, statename + '24.zip')
    zf = zipfile.ZipFile(zipfilename, 'r')
    for zipname in zf.namelist():
        if not zipname.lower().endswith('.csv'):
            continue

        # Now integrate the voting data into the json
        # Give a string path to the ZIP archive, and
        # the archived file to read from
        # Thanks to https://stackoverflow.com/a/70583472
        # and a ridiculously long string of changing methods
        zf = zipfile.Path(zipfilename, at=zipname)

        # Then use the open method, like you'd usually use the built-in open()
        csv_f = zf.open(newline='')

        # Pass the TextIO-like file to your reader as normal
        for row in csv.DictReader(csv_f):
            # Relevant fields:
            #    precinct ('PCT 001') matches VTD/VTD_NUM in the GIS
            #      note they're unique to a county, not whole state
            #    office ('US PRESIDENT')
            #    party_detailed (REPUBLICAN, DEMOCRAT, etc)
            #    votes (an int, or *)
            #    county_fips (35028)
            #    jurisdiction_name (LOS ALAMOS)
            #    state_po (NM)
            #    state_fips (35)

            if row['office'] != 'US PRESIDENT':
                continue
            # print("row:", row)

            # The CSV sometimes has ''PCT 001', sometimes 'PRECINCT 160'
            # so parse the first digit group and hope ...
            try:
                rowprecinct = int(re.search(r'[0-9]+', row['precinct']).group(0))
            except Exception as e:
                print("Couldn't parse precinct from '%s'" % row['precinct'],
                      e, file=sys.stderr)
                continue

            # Find the matching object in the geojson
            for feature in precinctjson['features']:
                if (feature['properties']['COUNTY_NAM'].lower()
                    == row['jurisdiction_name'].lower()
                    and feature['properties']['VTD_NUM'] == rowprecinct):
                    # It's a match.
                    # print("Adding", row['votes'],
                    #       row['party_detailed'], "votes in",
                    #       row['jurisdiction_name'],
                    #       feature['properties']['VTD_NUM'])
                    if 'votes' not in feature['properties']:
                        feature['properties']['votes'] = {}
                    # The MIT data gives '*' if no votes.
                    # And sadly, csv reads this integer column as a string
                    # for all rows, maybe because of the '*' in some rows.
                    try:
                        votes = int(row['votes'])
                    except:
                        votes = 0
                    feature['properties']['votes'][row['party_detailed']] = votes
                    # Done with looping over precinctjson, go on to the next row
                    debugfound = True
                    break
                # else:
                #     print(feature['properties']['COUNTY_NAM'].lower(),
                #           "didn't match", row['jurisdiction_name'].lower(),
                #           "or", feature['properties']['VTD_NUM'],
                #           "didn't match", row['precinct'].split()[-1],
                #           "(from", row['precinct'], ")")

    # All the votes are in. Calculate the purple coefficient.
    for feature in precinctjson['features']:
        props = feature['properties']
        if ('REPUBLICAN' not in props['votes']
            or 'DEMOCRAT' not in props['votes']):
            print(props['COUNTY_NAM'], props['VTD_NUM'],
                  "doesn't have votes for both R and D:", props, file=sys.stderr)
            continue
        if props['votes']['REPUBLICAN'] + props['votes']['DEMOCRAT'] == 0:
            print(props['COUNTY_NAM'], props['VTD_NUM'],
                  "has no votes for either D or R", file=sys.stderr)
            continue
        feature['properties']['R-vs-D'] = (
            props['votes']['REPUBLICAN'] /
            (props['votes']['REPUBLICAN'] + props['votes']['DEMOCRAT']))

    # Move the items inside "votes" outside it, so they can be formatted
    # more nicely by folium.
    for feature in precinctjson['features']:
        props = feature['properties']
        for party in props['votes']:
            props[party] = props['votes'][party]
        del props['votes']

    # Now write the new GeoJSON
    with open(outfilename, 'w') as fp:
        json.dump(precinctjson, fp, indent=2)
        print("Wrote to", outfilename)


def purplestyle(feature):
    """Style each precinct according to its R-vs-D votes"""
    r = feature['properties']['REPUBLICAN']
    d = feature['properties']['DEMOCRAT']
    if r + d:
        fill_color = '#%02x00%02x' % (int(0xff * r/(r+d)), int(0xff * d/(r+d)))
    else:
        fill_color = '#ffffff'
    # print("fill color:", fill_color)
    return {
        'fillColor': fill_color,
        'color': 'white',
        'weight': 1,
    }


def highlight_feature(feature):
    """Called when mousing over a feature"""
    return {
        'color': 'black',
        'weight': 3
    }


def make_map(jsonfilename):
    m = folium.Map(location=(34.4, -106.1), zoom_start=8)
    folium.TileLayer("", name="No basemap", attr="blank", show=False).add_to(m)

    # Should maybe get this from reading the geojson, but
    # what a drag to have to read such a huge file as a separate step
    # just to get the list of parties
    parties = ['REPUBLICAN', 'DEMOCRAT', 'LIBERTARIAN', 'GREEN',
               'INDEPENDENT', 'SOCIALISM AND LIBERATION']

    folium.GeoJson(jsonfilename, name="Voting",
                   style_function=purplestyle,
                   highlight_function=highlight_feature,
                   # popups on click:
                   popup=folium.GeoJsonPopup(
                       fields=['COUNTY_NAM', 'VTD_NUM', 'POP', 'R-vs-D']
                               + parties,
                       aliases=['County:', 'Precinct:', 'Population', 'R-vs-D']
                               + parties,
                   ),
                   # Tooltips on mouseover:
                   # tooltip=folium.features.GeoJsonTooltip(
                   #     fields=['COUNTY_NAM', 'VTD_NUM', 'votes'],
                   #     aliases=['County:', 'Precinct:', 'Votes'])
                   ).add_to(m)

    folium.LayerControl().add_to(m)

    htmlfilename = "map.html"
    m.save(htmlfilename)
    print("Saved to", htmlfilename)


if __name__ == '__main__':
    statename = 'nm'
    jsonfilename = statename + '-precinct-data.json'
    if not os.path.exists(jsonfilename):
        print("Generating", jsonfilename, "...")
        create_geojson('nm-VTD.json',
                       '2024-elections-official/individual_states',
                       statename, jsonfilename)
    else:
        print(jsonfilename, "already exists, not regenerating")

    make_map(jsonfilename)
