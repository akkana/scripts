#! /usr/bin/env python

# Print a table of mean temperatures (and other weather data) per month
# for several locations.
#
# Copyright 2013 by Akkana Peck.
#
# This program is free software; you can redistribute it and/or
#        modify it under the terms of the GNU General Public License
#        as published by the Free Software Foundation; either version 2
#        of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
#        but WITHOUT ANY WARRANTY; without even the implied warranty of
#        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#        GNU General Public License for more details.
# The licence text is available online at:
#        http://www.gnu.org/licenses/gpl-2.0.html
#

import sys, os

class WeatherMean :
    '''Weather means for one location, over an extended period,
       encompassing means for several different fields keyed by
       name (e.g. MAX for high temp, MIN for low temp), averaged
       by month.
    '''
    def __init__(self, fields) :
        self.tots = {}
        self.num_obs = {}
        self.normalized = False
        for field in fields :
            self.tots[field] = [0.0] * 12
            self.num_obs[field] = [0] * 12

    def add_obs(self, line) :
        '''Add observations for every field we're tracking
           by parsing a line from a data file.
           Increment nobs if the field isn't undefined.
           This method is undefined in the base class;
           derived classes should override it.
        '''
        raise NotImplementedError

    def normalize(self) :
        for field in self.tots.keys() :
            for month in range(12) :
                if self.num_obs[field][month] > 0 :
                    self.tots[field][month] /= self.num_obs[field][month]
        self.normalized = True

    def get_data(self, field) :
        '''Return the 12-month means for the indicated field name.'''
        if not self.normalized :
            self.normalize()
        return self.tots[field]

