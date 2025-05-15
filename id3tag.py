#!/usr/bin/env python3

import musicbrainzngs

# Tried to use mutagen to write the updated tags, but the examples
# in the documentation save() a file that id3tool still can't read
# and pygame's audio player can no longer play it.
#from mutagen.id3 import ID3, TIT2
# So instead, use the id3 commandline program to change tags.
import subprocess

# For parsing dates
from datetime import datetime

# fuzzy searches
from difflib import SequenceMatcher

import sys, os


Debug = True

def add_id3_tags(filename, title=None, album=None, artist=None, year=None):
    # XXX Should probably switch to using id3v2 (a different program)
    args = [ 'id3', '-T', '5' ]
    if title:
        args += [ '-t', title ]
    if album:
        args += [ '-A', album ]
    if artist:
        args += [ '-a', artist ]
    if year:
        args += [ '=y', str(year) ]

    # Done with args, filename goes last
    args.append(filename)

    if Debug:
        print("Calling:", args)
    subprocess.call(args, shell=False)


def get_album_info(args):
    """Return album_info, artist, album_title
       where album_info is the musicbrainz structure.
    """
    musicbrainzngs.set_useragent("Disk Lookerupper", "0.1",
                         "https://github.com/alastair/python-musicbrainzngs/")

    if len(sys.argv) == 2 and len(sys.argv[1]) == 36:
        album_id = sys.argv[1]
        artist = None
        album_title = None

    elif len(sys.argv) == 3:
        artist, album_title = sys.argv[1:3]
        albums = musicbrainzngs.search_releases(artist=artist,
                                                release=album_title,
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
    return album_info, artist, album_title


def update_dir(album_info, artist, album_title, dirname='.'):
    filenames = sorted(os.listdir(dirname))
    file_matches = {}
    file_nomatches = {}

    ndiscs = len(album_info["release"]['medium-list'])

    for filename in filenames:
        if not filename.lower().endswith('.mp3'):
            print("Skipping", filename, ": not MP3")
            continue
        if Debug:
            print("filename", filename)
        filenamebase = os.path.splitext(filename)[0]
        MIN_RATIO = .88
        best_ratio = MIN_RATIO
        best_match = None
        for discno, medium in enumerate(album_info["release"]['medium-list']):
            for trackno, track in enumerate(medium['track-list']):
                # Replace spaces with underscores.
                # Try both with and without the track number prepended.
                trackname = track['recording']['title'].replace(' ', '_')
                if ndiscs > 1:
                    trackname_n = '%d-%02d_%s' % (discno+1, trackno+1,
                                                  trackname)
                else:
                    trackname_n = '%02d_%s' % (trackno+1, trackname)
                r = SequenceMatcher(None, trackname, filenamebase).ratio()
                r_n = SequenceMatcher(None, trackname_n, filenamebase).ratio()
                if Debug:
                    print("  ", trackname_n, "has ratio", r_n)
                r_best = max(r, r_n)
                if r_best > best_ratio:
                    if Debug:
                        print("Hooray,", filename, "matched")
                    file_matches[filename] = track
                    best_match = r_best

    if Debug:
        print("Matches:")
    for filename in filenames:
        if filename in file_matches:
            if Debug:
                print(filename, '...',
                      file_matches[filename]['recording']['title'])
        else:
            file_nomatches[filename] = filenamebase.replace('_', ' ')
            if Debug:
                print(filename, '... (', file_nomatches[filename], ')')

    ans = input("Tag all files in the current directory? (y) ")
    if ans.lower().startswith('n'):
        print("Not making changes")
        return

    # musicbrainz has date while the id3 program only handles 4-digit year
    # The musicbrainz date seems to be in YYYY-mm-dd format.
    try:
        year = int(album_info['date'][:4])
        if Debug:
            print("Year is", year)
    except Exception as e:
        if Debug:
            print("Couldn't parse date:", e)
        from pprint import pprint
        pprint(album_info)
        year = None

    for filename in filenames:
        if filename not in file_matches:
            print("Skipping", filename)
            continue
        print("Changing", filename)
        add_id3_tags(filename,
                     title=file_matches[filename]['recording']['title'],
                     album=album_title, artist=artist, year=year)


if __name__ == '__main__':
    album_info, artist, album_title = get_album_info(sys.argv[1:])

    for medium in album_info["release"]['medium-list']:
        print("\nDisc %s:" % medium['position'])
        for track in medium['track-list']:
            print('%s: %s' % (track['position'],
                              track['recording']['title']))

    # Weirdly, musicbrainz album structures don't always have artist or title
    update_dir(album_info, artist, album_title)
