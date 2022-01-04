#!/usr/bin/env python3

# Reset Firefox's zoom settings.
# I mostly use zoom because I'm on the laptop instead of the big monitor,
# not because a particular site needs zooming in general.
# So I don't want firefox to keep

# How this works:
# Firefox stores zoom info in content-prefs.sqlite.
# select id,name from settings where name like '%zoom%';
# then use that id for:
# select id,groupID,value from prefs where settingID is 2;
# If curious, the site names are in groups which has columns id, name.

import sqlite3
import sys, os


def get_zoom_id(cursor):
    # Get the ID for zoom
    cursor.execute("select id,name from settings where name like '%zoom%';")
    settings = cursor.fetchall()
    if len(settings) == 1:
        zoom_id, zoom_name = settings[0]
        if zoom_name == "browser.content.full-zoom":
            return zoom_id

        print("Unexpected zoom name:", zoom_name)
    else:
        print("Uh-oh, there's more than one zoom setting!")
        for id, name in settings:
            print(f"{id:4} {name}")

    return None


def show_zoom_info(contentfile):
    # The documentation says you can open in read-only mode
    # using URI syntax, but it doesn't work, still raises
    # sqlite3.OperationalError "database is locked"
    # uri = "file://" + os.path.abspath(contentfile) + "?mode=ro"
    # uri = "file:" + os.path.abspath(contentfile) + "?mode=ro"
    # print("Trying URI", uri)
    # conn = sqlite3.connect(uri, uri=True)

    # This is supposed to be an alternate way of opening in
    # read-only mode, but it doesn't work either:
    # fd = os.open(contentfile, os.O_RDONLY)
    # conn = sqlite3.connect('/dev/fd/%d' % fd)
    # (if you get this working, add os.close(fd) at function's end)

    # Since neither of those work, copy the file if necessary (sigh):
    tempcontent = None
    cursor = None
    try:
        conn = sqlite3.connect(contentfile)
        cursor = conn.cursor()
        zoom_id = get_zoom_id(cursor)

    except sqlite3.OperationalError:
        print("Database is locked. Making a copy of", contentfile)
        from tempfile import NamedTemporaryFile
        tempcontent = NamedTemporaryFile(mode="wb")
        with open(contentfile, "rb") as infp:
            tempcontent.write(infp.read())

        conn = sqlite3.connect(tempcontent.name)
        cursor = conn.cursor()
        zoom_id = get_zoom_id(cursor)

    cursor.execute("select id,groupID,value from prefs where settingID is ?;",
                   (zoom_id,))
    zoom_settings = cursor.fetchall()

    cursor.execute("select id, name from groups")
    groupnames = cursor.fetchall()

    print("Saved zoom settings:")
    for zs in zoom_settings:
        cursor.execute(f"select name from groups where id is ?;", (zs[1],))
        domain = cursor.fetchall()[0][0]
        print(f"{zs[2]:5}  {domain}")

    conn.close()


def clear_zoom_info(contentfile):
    conn = sqlite3.connect(contentfile)
    cursor = conn.cursor()

    zoom_id = get_zoom_id(cursor)

    cursor.execute("delete from prefs where settingID is ?;", (zoom_id,))

    conn.commit()
    conn.close()

    print("Deleted all zoom settings")


def Usage():
    progname = os.path.basename(sys.argv[0])
    print("""%s: Explore firefox zoom settings.

Usage:
    Show current zoom levels:
        %s /path/to/content-prefs.sqlite
    Delete all saved zoom levels:
        %s -d /path/to/content-prefs.sqlite

Make sure firefox is NOT running when changing content-prefs.sqlite."""
                  % (progname, progname, progname))
    sys.exit(0)


if __name__ == '__main__':
    try:
        if sys.argv[1] == '-h' or sys.argv[1] == "--help":
            raise IndexError

        if sys.argv[1] == '-d':
            clear_zoom_info(sys.argv[2])

        else:
            show_zoom_info(sys.argv[1])

    except IndexError:
        Usage()

    # except sqlite3.OperationalError as e:
    except RuntimeError as e:
        print("OperationalError:", e)
        print("""
Either ensure that firefox is not running, or (if you're just trying
to view current zoom settings) use a copy of content-prefs.sqlite""")
        sys.exit(1)
