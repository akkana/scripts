#!/usr/bin/env python3

import musicbrainzngs

# Tried to use mutagen to write the updated tags, but the examples
# in the documentation save() a file that id3tool still can't read
# and pygame's audio player can no longer play it.
#from mutagen.id3 import ID3, TIT2
# So instead, use the id3 commandline program:
import subprocess

# fuzzy searches
from difflib import SequenceMatcher

import sys, os


def add_id3_tags(filename, title=None, album=None, artist=None, year=None):
    args = [ 'id3', '-T', '5' ]
    if title:
        args += [ '-t', title ]
    if album:
        args += [ '-A', album ]
    if artist:
        args += [ '-a', artist ]
    if year:
        args += [ '=y', str(year) ]

    print("Calling:", args)
    subprocess.call(args, shell=False)


def get_album_info(args):
    musicbrainzngs.set_useragent("Disk Lookerupper", "0.1",
                         "https://github.com/alastair/python-musicbrainzngs/")

    if len(sys.argv) == 2 and len(sys.argv[1]) == 36:
        album_id = sys.argv[1]

    elif len(sys.argv) == 3:
        artist, album = sys.argv[1:3]
        albums = musicbrainzngs.search_releases(artist=artist, release=album,
                                                limit=10)

        for i, album in enumerate(albums["release-list"]):
            if 'status' in album:
                status = album['status']
            else:
                status = 'no status'
            if 'date' in album:
                d = album['date']
            else:
                d = 'unknown date'
            if 'country' in album:
                country = album['country']
            else:
                country = "no country"
            if 'disambiguation' in album:
                dis = album['disambiguation']
            else:
                dis = ""
            if 'packaging' in album:
                pkg = album['packaging']
            else:
                pkg = 'no packaging'

            numtracks = []
            for medium in album['medium-list']:
                if 'track-count' in medium:
                    numtracks.append(medium['track-count'])
                else:
                    numtracks.append[0]
            ntstr = '%d tracks' % sum(numtracks)
            if len(numtracks) > 1:
                ntstr += ' (%s)' % '+'.join([ str(nt) for nt in numtracks ])

            print("%d: %s %s (%d disc)\n    %s, %s, %s, %s %s, %s\n"
                  % (i, album['id'], album['title'], album['medium-count'],
                     status, d, country, pkg, dis, ntstr))

        while True:
            choicestr = input("Choice (0) or q: ").strip()
            if not choicestr:
                choice = 0
                break
            elif choicestr == 'q':
                sys.exit(0)
            else:
                try:
                    choice = int(choicestr)
                    break
                except:
                    print("Sorry, can only accept a number, not '%'"
                          % choicestr)

        album_id = albums["release-list"][choice]["id"]
        print("Using album", album_id)

    else:
        print("Usage: %s artist album" % (os.path.basename(sys.argv[0])))
        print("       %s album_id" % (os.path.basename(sys.argv[0])))
        sys.exit(1)

    album_info = musicbrainzngs.get_release_by_id(album_id,
                                                  includes=["recordings"])
    return album_info


if __name__ == '__main__':
    album_info = get_album_info(sys.argv[1:])
    # update_dir()

    for medium in album_info["release"]['medium-list']:
        print("\nDisc %s:" % medium['position'])
        for track in medium['track-list']:
            print('%s: %s' % (track['position'],
                              track['recording']['title']))
