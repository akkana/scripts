#!/usr/bin/env python

# A flexible 2D Cellular Automata computation and display engine in Python.

# Copyright 2013 by Akkana Peck.
# Share and enjoy under the terms of the GPL v2 or later.

import time
import random

class Cellgrid:
    def __init__(self, nrows, ncols):
        self.nrows = nrows
        self.ncols = ncols
        self.grid = [[0] * ncols for i in xrange(nrows)]
        self.characters = None

    def item(self, coords):
        '''Return the item at the given coordinates,
           accounting for periodic boundary conditions.
        '''
        return self.grid[coords[0] % self.nrows][coords[1] % self.ncols]

    def setitem(self, coords, val):
        '''Set the given item to the given value.
        '''
        self.grid[coords[0] % self.nrows][coords[1] % self.ncols] = val

    def update(self, rule):
        '''Update self.grid using the given rule.
           Replaces self.grid with the new grid.
           rule should have the signature
           rule(cellgrid, (row, col)) -> int
        '''
        self.newgrid = []
        for r in xrange(self.nrows):
            self.newgrid.append([])
            for c in xrange(self.ncols):
                self.newgrid[r].append(rule(self, (r, c)))

        self.grid = self.newgrid

    def __repr__(self):
        out = ''
        for row in self.grid:
            for cell in row:
                if self.characters:
                    out += self.characters[cell]
                else:
                    out += '%3d' % cell
            out += '\n'
        return out

if __name__ == "__main__" :
    def addone(cellgrid, coords):
        return cellgrid.item(coords) + 1

    def life(cellgrid, coords):
        # Count the total number of neighbors, not including the cell itself:
        tot = 0
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                if i == 0 and j == 0:
                    continue
                tot += cellgrid.item((coords[0]+i, coords[1]+j))
        # With 3 neighbors, there will always be a cell there:
        if tot == 3:
            return 1
        # 2 neighbors lets an existing cell live on:
        if tot == 2 and cellgrid.item(coords):
            return 1
        # Otherwise it dies, of lonliness or overcrowding:
        return 0

    cellgrid = Cellgrid(10, 10)

    # Initialize with a glider:
    cellgrid.setitem((0, 2), 1)
    cellgrid.setitem((1, 2), 1)
    cellgrid.setitem((2, 2), 1)
    cellgrid.setitem((2, 1), 1)
    cellgrid.setitem((1, 0), 1)

    # Show characters, not numbers:
    #cellgrid.characters = '.*'
    cellgrid.characters = [' .', ' *' ]

    while True:
        print ""
        print "====================="
        print cellgrid
        cellgrid.update(life)
        time.sleep(.1)
