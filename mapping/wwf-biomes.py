#!/usr/bin/env python

# Analyze the WWF Terrestrial Ecoregions of the World shape files,
# http://www.worldwildlife.org/publications/terrestrial-ecoregions-of-the-world
# Dependencies: shpUtils.py and dbfUtils.py, both from
# http://indiemaps.com/blog/2008/03/easy-shapefile-loading-in-python/

import shpUtils

shpRecords = shpUtils.loadShapefile('wwf_terr_ecos.shp')
print "Loaded the shape file"

# The list of biomes defined in wwf_terr_ecos.htm :
biomes = [
    "BIOME 0",    # should never occur
    "Tropical & Subtropical Moist Broadleaf Forests",
    "Tropical & Subtropical Dry Broadleaf Forests",
    "Tropical & Subtropical Coniferous Forests",
    "Temperate Broadleaf & Mixed Forests",
    "Temperate Conifer Forests",
    "Boreal Forests/Taiga",
    "Tropical & Subtropical Grasslands, Savannas & Shrublands",
    "Temperate Grasslands, Savannas & Shrublands",
    "Flooded Grasslands & Savannas",
    "Montane Grasslands & Shrublands",
    "Tundra",
    "Mediterranean Forests, Woodlands & Scrub",
    "Deserts & Xeric Shrublands",
    "Mangroves",
    # WWF, at least, uses 99 for unknown biome.
    ]

def print_biome_list():
    for i in range(0, len(shpRecords)):
        biome = int(float(shpRecords[i]['dbf_data']['BIOME']))
        if shpRecords[i]['shp_data']['numparts'] != 1:
            extra = " ====== " + \
                    str(shpRecords[i]['shp_data']['numparts']) + " parts"
        else:
            extra = ""

        try:
            print "%4d %s : %s (%d)%s" % \
                (i, shpRecords[i]['dbf_data']['ECO_NAME'].strip(),
                 biomes[biome], biome, extra)
        except:
            print "%4d %s : eek (%d)%s" % \
                (i, shpRecords[i]['dbf_data']['ECO_NAME'].strip(),
                 biome, extra)

print_biome_list()

# Plot the shapes. Can't actually do this because it needs too much RAM.
import matplotlib.pyplot as plt
def plot_shapes():
    for i in range(0, len(shpRecords)):
        x = []
        y = []
        for j in range(0,len(shpRecords[i]['shp_data']['parts'][0]['points'])):
            tempx = float(shpRecords[i]['shp_data']['parts'][0]['points'][j]['x'])
            tempy = float(shpRecords[i]['shp_data']['parts'][0]['points'][j]['y'])
            x.append(tempx)
            y.append(tempy)
            plt.fill(x,y)

    print "About to plot"
    plt.axis('equal')
    plt.title("Testing")
    plt.show()

# plot_shapes()

