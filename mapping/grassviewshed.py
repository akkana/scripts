#!/usr/bin/env python3

# Create a GRASS temporary location, import a DEM file,
# compute a viewshed and save it.

import sys, os
import shutil

# Must set this before importing grass:
gisbase = '/usr/lib/grass76'
os.environ['GISBASE'] = gisbase

# grass of course isn't in the standard Python library location
sys.path.insert(1, os.path.join(gisbase, 'etc', 'python'))
import grass.script as grass
import grass.script.setup as gsetup

gisdb = os.path.expanduser('~/grass/grassdata')

def grass_temp_location(templocation):
    # Other variables needed to set up a location
    # mapset name apparently has to be "PERMANENT" even for temporary locations.
    mapset = 'PERMANENT'

    # gisdb must already exist.
    if not os.path.exists(gisdb):
        os.makedirs(gisdb)

    rcfile = gsetup.init(gisbase, gisdb, templocation, mapset)
    print("Set up grass; rc file is", rcfile)

    grass.run_command('g.proj', flags='c', georef=demfile,
                      location=templocation)

    # The previous command says,
    # You can switch to the new location by
    # `g.mapset mapset=PERMANENT location=templocation`
    # but if you actually do, it beeps and complains that
    # <PERMANENT> is already the current mapset
    # grass.run_command('g.mapset', location=templocation, mapset=mapset)

def compute_viewshed(demfile, obs_lon, obs_lat, viewshedname, extension='tif'):
    '''Use GRASS r.viewshed to compute a viewshed for the given DEM file
       and observer longitude and latitude (in degrees),
       saving the output to viewshedname.extension.
       Currently only tif and png output are supported.
    '''
    demname = 'dem'
    viewshedfile = viewshedname + '.' + extension

    if extension == 'tif':
        grassoutfmt = 'GTiff'
    elif extension == 'png':
        grassoutfmt = 'PNG'
    else:
        raise RuntimeError("Can't handle extension " + extension)

    # Read in the DEM file
    grass.run_command('r.in.gdal', input=demfile, output=demname,
                      overwrite=True)

    grass.run_command('r.viewshed',
            input=demname,
            output=viewshedname,
            coordinate=[obs_lon, obs_lat],
            observer_elevation=10,
            overwrite=True)

    grass.run_command("r.out.gdal", input=viewshedname, overwrite=True,
                      output=viewshedfile, format=grassoutfmt)
    print("Wrote (hopefully)", viewshedfile)

def cleanup(templocation):
    # Clean up the temp location:
    shutil.rmtree(os.path.join(gisdb, templocation))


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: %s demfile observer_lon observer_lat"
              % os.path.basename(sys.argv[0]))
        sys.exit(1)

    demfile = sys.argv[1]
    obs_lon = float(sys.argv[2])
    obs_lat = float(sys.argv[3])

    templocation = 'templocation'

    grass_temp_location(templocation)
    compute_viewshed(demfile, obs_lon, obs_lat, 'viewshed')
    cleanup(templocation)
