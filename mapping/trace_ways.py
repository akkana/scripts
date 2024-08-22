#!/usr/bin/env python3

from OSMPythonTools.overpass import Overpass
overpass = Overpass()
from OSMPythonTools.overpass import overpassQueryBuilder

# Even though the OSM Api isn't used directly here,
# it's used by OSMPythonTools and if it's not imported here,
# .geometry() will die with
# Exception: module 'OSMPythonTools' has no attribute 'api'
from OSMPythonTools.api import Api

# Start with a query about powerlines in a fixed bbox.
# Obviously this could be generalized.
query = overpassQueryBuilder(bbox=[35.236646, -106.710205,
                                   36.2551715, -105.9002583],
                             elementType='way',
                             selector='"power"="line"',
                             out='body')
allways = overpass.query(query).ways()

connecting_ways = {}

VERBOSE = False


def find_starting_way(way_id):
    if type(way_id) is str:
        way_id = int(way_id)
    for line in allways:
        if line.id() == way_id:
            return line
    raise RuntimeError(f"No way with ID {way_id}")


def find_connecting_ways(startway):
    """Starting with a way, find other allways that connect to it,
       and add them to the global connecting_ways dict.
       For now, only consider lines that join to the start or end point.
    """
    if not connecting_ways:
        connecting_ways.append(startway)

    startway_nodes = startway.nodes()
    startstart = startway_nodes[0].id()
    startend = startway_nodes[-1].id()
    newways = []
    oldconnections = []
    if VERBOSE:
        print("\n=========================\nLooking for connections from",
              startway.id(), "with start", startstart, "end", startend)

    for testway in allways:
        try:
            testname = testway.tag('name')
        except:
            testname = ""
        if VERBOSE:
            print("  testing against way", testway.id(), testname)

        # already connected?
        if testway.id() in connecting_ways:
            if testway.id() != startway.id():
                if VERBOSE:
                    print("   found", testway.id(),
                          "is already in connecting_ways")
                oldconnections.append(testway.id())
            continue

        testnodes = testway.nodes()

        # Do the start or end nodes match start or end nodes of startway?
        teststart = testnodes[0].id()
        testend = testnodes[-1].id()
        if teststart == startstart or teststart == startend \
           or testend == startstart or testend == startend:
            connecting_ways[testway.id()] = testway
            if VERBOSE:
                print("    found a connecting node", testway.id())
            newways.append(testway)
        elif VERBOSE:
            print("   ", testway.id(), " doesn't connect:", teststart, testend)

    if VERBOSE:
        print(startway.id(), "found", len(newways), "new connections",
              [ w.id() for w in newways ],
              "and", len(oldconnections), "old ones", oldconnections)
    return newways


def save_connected_geometry(outname):
    """Save connecting_ways to a GPX file.
    """
    with open(outname, 'w') as outfp:
        print('''<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<gpx version="1.1" creator="trace_ways.py" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">''',
              file=outfp)

        for wayid in connecting_ways:
            way = connecting_ways[wayid]
            tags = way.tags()
            geom = way.geometry()
            # print(geom)
            if geom["type"] != "LineString":
                print(f"""ERROR: way {wayid} is '{geom["type"]}' instead of LineString""")
                continue
            print

            # geometry is a list of [lon, lat] pairs
            print("  <trk>", file=outfp)
            print("    <trkseg>", file=outfp)
            if "name" in tags and tags["name"]:
                name = tags["name"]
            else:
                name = f"Way {way.id()}"
            print(f"      <name>{name}</name>", file=outfp)

            for lon, lat in geom["coordinates"]:
                print(f'      <trkpt lat="{lat}" lon="{lon}"></trkpt>',
                      file=outfp)

            print("    </trkseg>", file=outfp)
            print("  </trk>\n", file=outfp)

        print("</gpx>", file=outfp)

    print("Wrote", outname)


if __name__ == '__main__':
    startway = find_starting_way('14597839')  # 'Pajarito - BA line'
    # startway = find_starting_way('14598545')
    connecting_ways[startway.id()] = startway
    newways = find_connecting_ways(startway)
    # Iterate over new nodes in no particular order,
    # adding even newer nodes each time until there's nothing.
    while newways:
        # print(len(newways), "new nodes")
        nextnode = newways.pop()
        newernodes = find_connecting_ways(nextnode)
        for n in newernodes:
            if n not in newways:
                newways.append(n)

    print("\nFound", len(connecting_ways), "connecting ways:")
    for wayid in connecting_ways:
        try:
            name = connecting_ways[wayid].tag('name')
        except:
            name = None
        if name:
            name = '"%s"' % name
        else:
            name = ''
        print(wayid, name)
        # print(connecting_ways[wayid].tags())

    save_connected_geometry("powerlines.gpx")

