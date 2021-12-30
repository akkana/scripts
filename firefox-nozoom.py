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
    conn = sqlite3.connect(contentfile)
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
        print(f"{zs[2]:5} {domain}")

    conn.close()

def clear_zoom_info(contentfile):
    conn = sqlite3.connect(contentfile)
    cursor = conn.cursor()

    zoom_id = get_zoom_id(cursor)

    cursor.execute("delete from prefs where settingID is ?;", (zoom_id,))

    conn.commit()
    conn.close()

    print("Deleted all zoom settings")


if __name__ == '__main__':
    import sys
    if sys.argv[1] == '-d':
        clear_zoom_info(sys.argv[2])
    else:
        show_zoom_info(sys.argv[1])

