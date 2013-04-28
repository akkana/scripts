#!/usr/bin/env python

# A flexible 2D Cellular Automata computation and display engine in Python.

# Copyright 2013 by Akkana Peck.
# Share and enjoy under the terms of the GPL v2 or later.

import time
import random
import gtk, gobject

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

    def run_plot(self, stepsecs=.1):
        '''Iterate over the rule, plotting the evolving grid
        '''
        

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

class CAWindow:
    def __init__(self, cellgrid, rule, timeout = 1):
        '''Timeout in milliseconds
        '''
        self.cellgrid = cellgrid
        self.rule = rule
        self.drawing_area = None
        self.fgc = None
        self.bgc = None
        self.width = 0
        self.height = 0
        self.timeout = timeout

    def draw(self):
        '''Draw the current state of the cell grid
        '''
        # Clear the background:
        self.drawing_area.window.draw_rectangle(self.bgc, True, 0, 0,
                                                self.width, self.height)

        # What's the size of each cell?
        w = self.width / self.cellgrid.ncols
        h = self.height / self.cellgrid.nrows

        # Draw the cells
        for r in xrange(self.cellgrid.ncols):
            for c in xrange(self.cellgrid.nrows):
                if cellgrid.item((r, c)):
                    self.fgc.set_rgb_fg_color(gtk.gdk.Color(65535, 0, 65535))
                else:
                    self.fgc.set_rgb_fg_color(gtk.gdk.Color(512, 512, 512))
                self.drawing_area.window.draw_rectangle(self.fgc, True,
                                                        c * w, r * h,
                                                        w, h)

    def expose_handler(self, widget, event):
        # print "Expose"
        if not self.fgc:
            self.fgc = widget.window.new_gc()
            self.bgc = widget.window.new_gc()
            self.bgc.set_rgb_fg_color(gtk.gdk.Color(0, 0, 0))

            self.width, self.height = self.drawing_area.window.get_size()

            # set a timeout
            gobject.timeout_add(self.timeout, self.idle_handler,
                                self.drawing_area)

        self.draw()

    def idle_handler(self, widget):
        self.cellgrid.update(self.rule)
        self.draw()

        # Return True so we'll be called again:
        return True

    def run(self):
        win = gtk.Window()
        self.drawing_area = gtk.DrawingArea()
        self.drawing_area.connect("expose-event", self.expose_handler)
        win.add(self.drawing_area)
        self.drawing_area.show()
        win.connect("destroy", gtk.main_quit)
        win.set_default_size(512, 512)

        win.show()
        gtk.main()

if __name__ == "__main__":
    # Some sample rules:

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

    # Set up the grid:
    cellgrid = Cellgrid(100, 100)

    # Initialize with a glider:
    cellgrid.setitem((0, 2), 1)
    cellgrid.setitem((1, 2), 1)
    cellgrid.setitem((2, 2), 1)
    cellgrid.setitem((2, 1), 1)
    cellgrid.setitem((1, 0), 1)

    # Show characters, not numbers:
    #cellgrid.characters = '.*'
    cellgrid.characters = [' .', ' *' ]

    cawin = CAWindow(cellgrid, life)
    cawin.run()

    print "Shouldn't ever get here"
    while True:
        print ""
        print "====================="
        print cellgrid
        cellgrid.update(life)
        time.sleep(.1)
