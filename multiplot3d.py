#!/usr/bin/env python3

from __future__ import print_function

# Adapted from
# https://stackoverflow.com/questions/13240633/matplotlib-plot-pulse-propagation-in-3d
# and rewritten to make it clearer how to use it on real data.

import numpy
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib import colors as mcolors

import random

def gen_data(xbins, numplots):
    '''Generate a list of random histograms'''
    data = []
    ymin = 9999999999999
    ymax = -ymin
    for plot in range(numplots):
        plotpoints = []
        y = random.randint(0, 5)
        for x in range(xbins):
            y += random.uniform(-.8, 1)
            ymin = min(ymin, y)
            ymax = max(ymax, y)
            plotpoints.append((x, y))
        data.append(plotpoints)
    return data, ymin, ymax

from matplotlib.pyplot import cm

def draw_3d(verts, ymin, ymax, line_at_zero=True, colors=True):
    '''Given verts as a list of plots, each plot being a list
       of (x, y) vertices, generate a 3-d figure where each plot
       is shown as a translucent polygon.
       If line_at_zero, a line will be drawn through the zero point
       of each plot, otherwise the baseline will be at the bottom of
       the plot regardless of where the zero line is.
    '''
    # add_collection3d() wants a collection of closed polygons;
    # each polygon needs a base and won't generate it automatically.
    # So for each subplot, add a base at ymin.
    if line_at_zero:
        zeroline = 0
    else:
        zeroline = ymin
    for p in verts:
        p.insert(0, (p[0][0], zeroline))
        p.append((p[-1][0], zeroline))

    if colors:
        # Make facecolors and edgecolors be a list of as many colors
        # as there are plots, i.e. len(verts) colors.
        # base_hue = mcolors.rgb_to_hsv(
        # mcolors.hsv_to_rgb(hsv)
        # basecolors = ['g', 'b', 'y', 'c', 'm' ]
        facecolors = []
        edgecolors = []
        rainbow = iter(cm.rainbow(numpy.linspace(0, 1, len(verts))))
        for v in verts:
            c = next(rainbow)
            edgecolors.append(c)
            c[-1] = .5
            facecolors.append(c)
    else:
        facecolors = (1, 1, 1, .8)
        edgecolors = (0, 0, 1, 1)

    poly = PolyCollection(verts,
                          facecolors=facecolors, edgecolors=edgecolors)

    zs = range(len(data))
    # zs = range(len(data)-1, -1, -1)

    fig = plt.figure()
    ax = fig.add_subplot(1,1,1, projection='3d')
    ax.add_collection3d(poly, zs=zs, zdir='y')

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    ax.set_xlim3d(0, len(data[1]))
    ax.set_ylim3d(-1, len(data))
    ax.set_zlim3d(ymin, ymax)


if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', "--color", dest="colors", default=False,
                        action="store_true", help="Plot in multiple colors")
    parser.add_argument('-x', action="store", dest="xbins",
                        type=int, default=50,
                        help='Number of points on the X axis')
    parser.add_argument('-n', action="store", dest="numplots",
                        type=int, default=5,
                        help='Number of plots')
    args = parser.parse_args(sys.argv[1:])

    data, ymin, ymax = gen_data(args.xbins, args.numplots)
    draw_3d(data, ymin, ymax, colors=args.colors)
    plt.show()


