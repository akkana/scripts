#!/usr/bin/env python3

"""Decode a .fit file exported by Specialized's ebicycle app.
   Save GPS information to a GPX file, and other data,
   like cadence, the bike's power setting, power usedb by the rider,
   etc. to a CSV.

   Requires the Python fit-decode package.
   Requires TrackPoints from PyTopo in order to export to GPX
   (without PyTopo, you'll just get CSV).
"""

CSV_KEYS = [ "timestamp", "latitude", "longitude", "enhanced_altitude",
             "distance", "enhanced_speed", "power", "cadence",
             "motor_power", "ebike_assist_mode", "ebike_battery_level",
             "grade", "gps elevation", "smoothed elevation"
            ]

import fitdecode
import sys

try:
    from pytopo import TrackPoints
except:
    print("Warning: couldn't import pytopo.TrackPoints, won't save GPX",
          file=sys.stderr)
    import subprocess

# Specialized fit uses "semicircles" for latitude and longitude.
SEMICIRCLES_TO_DEGREES = 180. / 0x80000000


def handle_gps_point(fields, trackpoints):
    """Convert the position_lat and position_long from semicircles to degrees,
       and add a trackpoint including other relevant fields.
       Return the newly created trackpoint.
    """
    try:
        timestamp = fields['timestamp']
    except KeyError:
        timestamp = None

    try:
        ele = fields['smoothed_elevation']
    except KeyError:
        try:
            ele = fields['gps_elevation']
        except KeyError:
            ele = None

    # Specialized uses values like 427269417 (lat) and -1267241539 (lon)
    # with units reported as "semicircles"
    fields['latitude'] = fields['position_lat'] * SEMICIRCLES_TO_DEGREES
    fields['longitude'] = fields['position_long'] * SEMICIRCLES_TO_DEGREES

    return trackpoints.handle_track_point(fields['latitude'],
                                          fields['longitude'],
                                          ele=ele, timestamp=timestamp)


def read_fit_file(filename, outgpxname=None, outcsvname=None):
    """Read a .fit file. Export to GPX and/or CSV files.
    """

    if outcsvname:
        outcsv = open(outcsvname, 'w')
        print(','.join(CSV_KEYS), file=outcsv)

    else:
        outcsv = None

    if outgpxname:
        if 'pytopo.TrackPoints' in sys.modules:
            trackpoints = TrackPoints()
        else:
            trackpoints = None
            # Try to use gpsbabel
            try:
                subprocess.call(["gpsbabel",
                                 "-i", "garmin_fit", "-f", filename,
                                 "-o", "gpx", "-F", outgpxname])
            except:
                print("Can't export trackpoints: need pytopo.TrackPoints module"
                      " or gpsbabel installed",
                      file=sys.stderr)
                outgpxname = None

    with fitdecode.FitReader(filename) as fit:
        for frame in fit:
            # The yielded frame object is of one of the following types:
            # * fitdecode.FitHeader (FIT_FRAME_HEADER)
            # * fitdecode.FitDefinitionMessage (FIT_FRAME_DEFINITION)
            # * fitdecode.FitDataMessage (FIT_FRAME_DATA)
            # * fitdecode.FitCRC (FIT_FRAME_CRC)

            if frame.frame_type == fitdecode.FIT_FRAME_DATA:
                # Here, frame is a FitDataMessage object.
                # A FitDataMessage object contains decoded values that
                # are directly usable in your script logic.
                # For Specialized fit files, frame.name is either
                # 'event' or 'record' or 'device_info'
                # records seem to be the ones with the useful data.
                # I'm not sure what event is for,
                # it doesn't seem to hold anything useful.
                # Also it spews lots of warnings like
                # UserWarning: 'field "native_field_num" (idx #0) not found in message "field_description"' (local_mesg_num: 0; chunk_offset: 112); adding dummy dev data...
                # fieldnames = [ f.name for f in frame.fields ]
                # print("\n", frame.name, "fields:", fieldnames)

                if frame.name != 'record':
                    continue

                # fieldnames = [ f.name for f in frame.fields ]
                # ['timestamp', 'position_lat', 'position_long', 'gps_accuracy', 'enhanced_altitude', 'altitude', 'absolute_pressure', 'distance', 'enhanced_speed', 'speed', 'power', 'cadence', 'motor_power', 'ebike_assist_mode', 'ebike_battery_level', 'enhanced_altitude', 'enhanced_speed', 'grade', 'position_lat_ignored', 'position_lon_ignored', 'smoothed elevation', 'gps elevation', 'altitude accuracy', 'gps speed', 'speed accuracy', 'bearing', 'motor_profile_scale', 'motor_current_scale']

                fields = {}
                # print("fields:", frame.fields)
                for f in frame.fields:
                    # print(f.name)
                    # print("    value:", f.value, type(f.value))
                    # print("    raw value:", f.raw_value, type(f.raw_value))
                    # print("    units:", f.units)
                    fields[f.name] = f.value

                if trackpoints is not None \
                   and 'position_lat' in fields and 'position_long' in fields \
                   and fields['position_lat'] and fields['position_long']:
                    handle_gps_point(fields, trackpoints)

                if outcsv:
                    out_line = ""
                    print(','.join([ str(fields[key])
                                     if key in fields
                                     else ''
                                     for key in CSV_KEYS
                                    ]),
                          file=outcsv)

    if outcsv:
        outcsv.close()
        if os.path.exists(outcsvname):
            print("Saved CSV to", outcsvname)
        else:
            print("Something went wrong saving CSV, sorry")

    if outgpxname:
        if trackpoints:
            trackpoints.save_GPX(outgpxname)
        if os.path.exists(outgpxname):
            print("Saved GPX to", outgpxname)
        else:
            print("Something went wrong saving GPX, sorry")
    else:
        print("Couldn't save GPX, need either gpsbabel or pytopo installed")


if __name__ == '__main__':
    import os
    for filename in sys.argv[1:]:
        base = os.path.splitext(filename)[0]
        read_fit_file(filename, outcsvname=base+".csv", outgpxname=base+".gpx")


