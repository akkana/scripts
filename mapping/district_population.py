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

    # Every other entry in the districts file is a point, a specific school.
    # Remove them so they don't get in the way later.
    districts = districts[districts.geom_type != 'Point']

    # To calculate area or intersection, results can be wrong with EPSG:4326;
    # apparently it's better to reproject to EPSG:4326 or EPSG:6933.
    # Initially, blocks uses EPSG:4269/NAD83 and districts, EPSG:4326/WGS 84.
    blocks = blocks.to_crs(epsg=6933)
    districts = districts.to_crs(epsg=6933)

    # Fill in the population from the census file DECENNIALPL2020.P1-Data.csv.
    # DECENNIALPL2020.P1-Column-Metadata.csv says total population
    # is the P1_001N field (the third field).
    # The first field of P1-Data, GEO_ID, is a number like
    # 1000000US350280001001000: the number after the "US", 350280001001000,
    # corresponds to GEOID20 in the block shapefile.
    # Column 2, NAME, is something like
    # "Block 1000, Block Group 1, Census Tract 1, Los Alamos County, New Mexico"

    # The US Census file begins with a bogus non-breaking space, feff.
    # Apparently Excel on Mac sometimes adds these at the beginning
    # of the file, for no known reason, but reading as utf-8-sig fixes it
    # for the python csv module.
    population_col = []
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

    blocks_in_districts = []
    distpops = []
    distno = 0
    for dist in districts.itertuples():
        # Plot the intersection of the current district
        # with the collection of all the blocks:
        # intersection = dist.geometry.intersection(blocks.geometry)
        # if not intersection.empty:
        #     intersection.plot()
        #     print("District", distno)
        #     plt.show()
        # else:
        #     print("District", distno, "doesn't intersect with any block")

        full_blocklist = []
        partial_blocklist = []
        areasum = 0
        population = 0

        for b in blocks.itertuples():
            # Find the intersection between this block and the current district
            intersect = dist.geometry.intersection(b.geometry)
            if not intersect:
                continue
            print("District", distno, "contains block", b.GEOID20)
            # intersect is a polygon, not a dataframe, so has no .geometry
            intersecting_area = intersect.area
            areasum += intersecting_area
            areafrac = intersecting_area / b.geometry.area
            print("  block population:", b.population)
            print("  intersecting_area:", int(intersecting_area),
                  "of", int(b.geometry.area),
                  "=", int(areafrac * 100), "%")
            if areafrac < .01:
                continue
            population_frac = int(b.population * areafrac)
            if population_frac < .01:
                continue
            population += population_frac
            if areafrac >= .99:
                full_blocklist.append(b.BLOCKCE20)
            else:
                partial_blocklist.append((b.BLOCKCE20, int(areafrac * 100)))

        print("district", distno, "includes all of blocks:",
              ' '.join(sorted(full_blocklist)))
        if partial_blocklist:
            partial_blocklist.sort()
            print("plus:",
                  ', '.join([ "%d%% of %s" % (percent, blockname)
                              for blockname, percent in partial_blocklist ]))
        print("  with area", dist.geometry.area, "and population", population)
        distpops.append(population)
        distno += 1

    # Sanity checks. Compare to the intersection of districts and blocks,
    # so the first step is to calculate that intersection.

    # This doesn't work: "The indices of the left and right GeoSeries' are
    # not equal, and therefore they will be aligned"
    # intersection = districts.geometry.intersection(blocks.geometry)

    # One page said this was equivalent to intersection, but it
    # gives an area that's 31 times too large, and when plotted,
    # it's clear that if how="left", it's just the union of all districts,
    #  and how="right" is the union of all blocks. Neither one
    # takes into account both left and right.
    # intersection = gpd.sjoin(left_df=districts, right_df=blocks,
    #                          how="left", predicate="intersects")

    # These actually seem to work:
    intersection = districts.overlay(blocks, how='intersection')
    # intersection = blocks.overlay(districts, how='intersection')

    # intersection.plot()
    # plt.show()

    print("Sum of areas:  ", areasum)
    print("block area:    ", sum(blocks.geometry.area))
    print("intersect area:", sum(intersection.geometry.area))
    print("Total population:", sum(population_col))
    print("District populations", distpops, '=', sum(distpops))


if __name__ == '__main__':
    population_in_districts('tl_2020_35028_tabblock20.shp',
                            'DECENNIALPL2020.P1-Data.csv',
                            'los-alamos-elementary-school-boundaries-2021.kmz')


    # District order in the kmz: Aspen, Barranca, Mountain,
    # Chamisa, Pinon
