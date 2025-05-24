#!/usr/bin/env python3

# Given a shapefile of US census blocks, a census CSV file with populations,
# and a shapefile with a set of districts (which may not follow the same
# boundaries as census blocks), produce a list of the estimated population
# in each district. (Assume population is evenly distributed through each
# census block.)

# https://pygis.io/docs/e_vector_overlay.html
# which also has some interesting Bay Area water data
# and a good discussion of types of joins,
# though unfortunately they only apply to the whole shapefile,
# not shape by shape.
# https://pythongis.org/part2/chapter-06/nb/08-overlay-analysis-with-vector-data.html
# is also useful and covers almost exactly the same concepts
# (though again, only for the whole shapefile).

import geopandas as gpd
import matplotlib.pyplot as plt
import csv
import sys


def population_in_districts(blockshapefile, popcsvfile, districtshapefile):
    # Load data
    blocks = gpd.read_file(blockshapefile)
    districts = gpd.read_file(districtshapefile)

    # To calculate area or intersection, results can be wrong with EPSG:4326;
    # apparently it's better to reproject to EPSG:4326 or EPSG:6933.
    # Initially, blocks uses EPSG:4269/NAD83 and districts, EPSG:4326/WGS 84.
    blocks = blocks.to_crs(epsg=6933)
    districts = districts.to_crs(epsg=6933)

    # XXX Do something here to get the total population column
    # from popcsvfile into blocks. This doesn't work:
    # blocks['population'] = None      # Initialize a new column in the dataframe
    # blocks['population'] = blocks['population'].astype('int')
    population_col = []

    # Fill in the population from the census file DECENNIALPL2020.P1-Data.csv.
    # DECENNIALPL2020.P1-Column-Metadata.csv says total population
    # is the P1_001N field (the third field).
    # The first field of P1-Data, GEO_ID, is a number like
    # 1000000US350280001001000: the number after the "US", 350280001001000,
    # corresponds to GEOID20 in the block shapefile.
    # Column 2, NAME, is something like
    # "Block 1000, Block Group 1, Census Tract 1, Los Alamos County, New Mexico"

    # The US Census file begins with a bogus non-breaking space.
    # Apparently Excel on Mac sometimes adds these at the beginning
    # of the file, for no known reason, but reading as utf-8-sig fixes it.
    with open('DECENNIALPL2020.P1-Data.csv', encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        for csvline in reader:
            try:
                geo_id = csvline['GEO_ID'].split('US')[1]
            except:
                # First line is a known issue:
                print("Problem parsing csv line:", csvline)
                continue
            blockrow = blocks.loc[blocks['GEOID20'] == geo_id]
            if blockrow.empty:
                print("Couldn't find a row matching", geo_id)
                continue
            population_col.append(int(csvline['P1_001N']))

    # print("population_col:", population_col)
    # print("Read", len(population_col), "from CSV, vs", blocks.shape)

    blocks['population'] = population_col

    #
    # print("Populations per block:")
    # print(blocks.to_string())

    # A test of one block
    # pinonparkblock = None
    # for b in blocks.itertuples():
    #     if b.GEOID20 == '350280005005005':  # ID of Pinon Park block
    #         print("Yippee!")
    #         pinonparkblock = b
    #         break

    blocks_in_districts = []
    distpops = []
    distno = 0
    for dist in districts.itertuples():
        # Every other district in the school district file is a point
        # indicating the location of that elementary school.
        # We only want to work with areas.
        if 'Polygon' not in dist.geometry.geom_type:
            continue

        # Plot the intersection of the current district
        # with the collection of all the blocks:
        # intersection = dist.geometry.intersection(blocks.geometry)
        # if not intersection.empty:
        #     intersection.plot()
        #     print("District", distno)
        #     plt.show()
        # else:
        #     print("District", distno, "doesn't intersect with any block")

        blocklist = []
        areasum = 0
        population = 0

        for b in blocks.itertuples():
            # Find the intersection between this block and the current district
            intersect = dist.geometry.intersection(b.geometry)
            if not intersect:
                continue
            print("District", distno, "contains block", b.GEOID20)
            blocklist.append(b.BLOCKCE20)
            intersecting_area = intersect.area
            areasum += intersecting_area
            print("  b.population:", b.population)
            print("  intersecting_area:", intersecting_area,
                  "of", b.geometry.area)
            population += int(b.population * intersecting_area / b.geometry.area)

        print("district", distno, "includes blocks:", ' '.join(sorted(blocklist)))
        print("with area", dist.geometry.area, "and population", population)
        distpops.append(population)
        distno += 1

    # Sanity check: does the total population work out?
    print("Total population:", sum(population_col))
    print("District populations", distpops, '=', sum(distpops))


if __name__ == '__main__':
    population_in_districts('tl_2020_35028_tabblock20.shp',
                            'DECENNIALPL2020.P1-Data.csv',
                            'los-alamos-elementary-school-boundaries-2021.kmz')


    # District order in the kmz: Aspen, Barranca, Mountain,
    # Chamisa, Pinon
