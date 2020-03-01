A collection of useful scripts and snippets, in various languges.

----------------
Subdirectories:
----------------

jsjupiter:
    My Jupiter's Moons Javascript web app: show the Galilean moons and
    their shadows, and predict transits, shadow transits and eclipses.

kobo:
    Module of utilities useful with Kobo ebook readers.

mapping:
    Scripts related to mapping / GIS.

mapping/election2016:
    Map blue-red-purple US presidential election results by county.

mailtests:
    Messages with attachments for testing viewmailattachments.

motioncam:
    An automated motion-sensitive camera driver, for Raspberry Pi or
    other machines. Requires pycamera module.

pycamera:
    A wrapper that can drive a Pi camera module, a USB webcam or an
    external gphoto2-compatible camera using similar APIs.

rpi:
    Scripts for the Raspberry Pi. Mostly wrappers to talk to sensors.

weather:
    Some attempts at accessing various weather APIs and plotting
    statistics.

--------------------------
Scripts in this directory:
--------------------------

analemma.py:
    Plot the analemma from the selected location, using PyEphem and PyGTK.

androidfiles.py:
    A Python module to make it easier to list files on an
    Android device using adb, and copy individual files to the device.
    Can also synchronize two directories, trying to notice when files
    need to be moved rather than removed and recopied.
    Used by podcopy.

animate.js:
    Simple code for animating a series of images in javascript.

aptver:
    Search for Debian packages, installed or uninstalled, matching
    a pattern, and print out versions and descriptions.

balanceparens.py:
    A very simple parenthesis (and brace and bracket) counter.
    Why isn't there a better one already on Linux?

birdcodes.py:
    Give common name for those obscure 4-letter bird codes.

bdump:
    Ascii/hex/decimal dumps of any file. Like od but much more readable.

bookfind.py:
    List books by author optionally year of publication,
    to find new books by particular authors.

cachefile.py:
    A general class for cases where you need to fetch data from some
    slow process, like a web API, and cache it locally for speedier access.
    Caches in CSV format.

cairodrawwin.py:
    A base for building Python3 GTK3/Cairo apps using a drawing area.
    You can import and subclass it, or use it as a template.

cellaut.py:
    Simple cellular automata simulation in Python. Slow.

censusdata.py
    Functions to help in parsing US decadal census data.

chatsounds.py:
    An xchat Python script to handle nick (and other special-case) sounds.
    Also a rare example of an xchat Python script.

check-monitors
    A shell script to probe for connected monitors and use xrandr to
    activate the right one. Obsoleted by monmon.py.

cleanhtml.py
    Clean up HTML edited by gmail users -- remove font/color/style tags
    and such. Then prettyprint (somewhat -- add newlines, at least).
    Minimal, but serves as an example for how to clean up HTML:
    every source may have different types of clutter, so you may need
    to customize for whatever source you're trying to clean up.

colormatch.php:
    Find the nearest matching color name. http://shallowsky.com/colormatch/

conjunctions.py:
    Predict planetary visibility and conjunctions for a specified
    date range.

countsyl:
    Count likely syllables in words, giving best guess and likely max.

decodemail.py:
    Decode email lines encoded in RFC 2047 format, printing only lines
    that match a specific header (Subject:, From:, etc.).

delaytest.cgi:
    A CGI script in Python that spits out some text slowly, with delays.
    Use it on your webserver (or localhost) to test things like parallel
    downloads to make sure they work with slow servers.

domaincheck.py:
    Check for expiring domains, using python-whois.

diff2rss:
    Diff two files and output RSS of the differences.
    A possible (though poor) solution for web pages that don't offer RSS feeds.

diffiles.py:
    Find files that differ between two directories -- even if
    they've been moved to different places in the directory structure.

docx2html, doc2html have been replaced by word2html.

eggtimer:
    Pop up a reminder window in a specified number of minutes.

epicycle.py:
    Show planet orbits as they would be viewed from the north ecliptic
    pole in a geocentric universe. Show the Venus Pentagram, etc.

epubtag.py:
    Display author, title and tag information for ebooks in epub format;
    or add or modify an ebook's topic tags, title or cover.
    Can be imported as a module (there are examples in the kobo/ directory
    and in fixbookcover).

falls_between.py:
    given a day of the week ("tue") or a day of the month (15),
    did it occur between two given dates?

fincompare.py:
    Download financial data from Yahoo finance and plot lots of
    different funds on the same scale.
    Can also take data from a local spreadsheet or other source.

fixbookcover:
    Fix books whose cover doesn't include the title, like many
    Project Gutenberg books.

fontasia:
    A Linux font chooser and categorizer.
    Also works as a GIMP plug-in font chooser.

fotogr:
    Find tagged photos: search for strings in files named Keyword or Tags
    beneath the current directory.

geojsonmap.py:
    How to plot a geojson file of polygons exported from QGIS.

gitbranchsync.py:
    Display git branches and what they're tracking,
    check whether a repository needs pushing upstream,
    and optionally make local branches track remotes of the same name.
    A solution to the problem of git making it idiotically difficult
    to keep several machines in sync with the branches in a git repository.

gpreso:
    A lightweight presentation program for displaying HTML slides.
    Python2/GTK/webkit version. (Previously called preso.)

greatcircle.py:
    Calculate bearings for a great circle trip between two coordinates
    on a spherical planet.

gquickbrowse:
    Minimal browser: an older version of quickbrowse written in
    python2-webkit-GTK, now orphaned and no longer available on newer
    releases. If you don't pass an argument but there's anything in
    the X selection when you run it, it will use that as initial argument.

grebook.sh:
    A shell script adapted from one by mosh on Stack Exchange
    to grep in un-DRMed epub (and presumably also mobi) ebooks.

grebook.py:
    A Python version of grebook, mainly useful to show how to implement
    a multi-stage command pipeline in Python.

htmlmail.py:
    Compose and send HTML mail, including image attachments.

hypermoon.py:
    Make up silly names for tonight's moon, as a CGI.

intel_backlight.py:
    Tiny script to adjust the backlight on an Intel-based laptop
    that uses /sys/class/backlight/intel_backlight.

imageviewer.py:
    A generic image viewer widget and image viewer window that can
    be imported into other python programs.

imageviewer3.py:
    A generic image viewer widget and image viewer window using GTK3
    via gi, so they can be used with Python 3.

ipsearch:
    Search for live hosts on the current net, or hosts with a
    particular port open..
    Useful for things like finding that Raspberry Pi you just booted.
    Also has some useful network wrappers like ping, arp, fping,
    list network interfaces and find current network.

ipscan:
    A Bourne shell (sh) net scanner/pi finder uses nmap.

keyreader.py
    Read characters (keystrokes) one at a time (cbreak mode),
    with or without blocking, with or without echo,
    on Unix/Linux/Posix platforms.

kitfox-patch
    A simple shell script to update Firefox's browser/omni.ja file
    with custom patches when a new version of Firefox comes out.

langgrep:
    Search (grep) for patterns only within scripts written in a
    specified language (e.g. in all python scripts).

louder:
    Increase alsa system volume by a small increment. Symlink it to
    another name like "quieter" and it will decrease instead.
    Bind those to volume increase/decrease keys on your laptop.
    and set it as the system wallpaper.

mac_lookup.p:
    Map MAC network addresses to manufacturers.
    Useful for things like scanning your network to find your Raspberry Pi.

masq:
    Set up IP masquerading to talk to another computer, such as a
    Raspberry Pi, over eth0 while using wlan0 for the internet.

mbsyncd:
    isync/mbsync is a good IMAP sync program, but for some bizarre reason
    it doesn't offer a daemon mode where it syncs regularly forever.
    So mbsyncd is a daemon wrapper for mbsync.

mnist.py:
    A simple example of a neural net using keras/tensorflow.

moncycle.py:
    Cycle between connected monitors (e.g. laptop display to HDMI).
    Can be bound to XF86Display in your window manager.

monmon.py
    Probe for connected monitors and their sizes and relative positions.
    Find "orphaned" windows (windows that are invisible offscreen)
    and move them back to a monitor that's still connected.
    Replaces and extends check-monitors.

moonpos:
    Predict when the moon (or another body) will be at a specified
    altitude and azimuth during a specified time window.

mouseevent.py:
    Read mouse events from /dev/input even if not running X,
    using the python evdev module. Linux only.

mpl_smart_dates.py:
    A smart date locator (ticker) and formatter for matplotlib
    that can autoadjust according to the amount of time the axis
    spans. Matplotlib's AutoDateLocator does this for major ticks,
    but doesn't offer the option of minor ticks.

mapping/demraytrace.py:
    Raytrace a Digital Elevation Model file using povray,
    creating a 360-degree panorama.
    demproj.py is similar but pointless, making lots of smaller
    povray projections that you can stitch together.

mapping/grassviewshed.py:
    Use GRASS r.viewshed for a viewshed analysis on a DEM input file.

mapping/polidistmap.py:
    Show political districts -- or any other geojson data -- on a map
    using folium to create a leaflet map.
    Also has examples for using gdal to translate shapefile to geojson.

mapping/shapemerge.py:
    Starting from a shapefile of New Mexico voting precincts, merge precincts
    to generate     shapefiles for House, Senate and US Congress districts.
    More generally, "dissolve" (merge) polygons in a shapefile according
    to their metadata, using fiona and shapely.

mapping/viewshed2view.py:
    Take a viewshed (like one generated by GRASS r.viewshed) and
    turn it into a 360 image showing what's visible.

multiplot3d.py:
    3D plots in matplotlib of a sequence of functions are so poorly
    documented, it took me ages to get one working. Here's a simple example.

mpcdemo.py:
    A tiny demo of how to use multiprocess communication in the
    multiprocessing module to start a worker thread and pass messages
    to it.

musicplayer.py:
    A little toy music player in Python, illustrating how to play audio.
    Actually more than a toy now -- I use it as my main music player.

noblank:
    Turn off screen blanking. Run this when you're giving a presentation.
    Linux-specific.

nokeywords:
    Find directories beneath the present one that don't contain a
    Keywords or Tags file -- i.e. image directories that need to be tagged
    with metapho.

nonblock.py, nonblock-py3.py:
    Examples of how to do nonblocking input in Py 2 and Py 3.
    For code that works in either version, see termsize.

noteplayer.py:
    Spun off of play_chord.py: a more general pygame-based  note generator
    usable asynchronously, like from a Raspberry Pi piano keyboard.

oppretro:
    Several different programs to examine Mars' orbit, and also to
    experiment with various astronomy libraries. See oppretro/README.md
    for more details.

pathmatch:
    Search your executable path to find programs matching a string.
    Like str<tab> except you can match patterns anywhere in the
    string, not just at the beginning.

phonewords.py:
    Map phone numbers to words, or vice versa. Find phone numbers
    that map to more than one word.

pisoothe:
    Play sound samples (e.g. soothing white or pink noise samples)
    in a loop, reacting to key events for volume control or to skip
    to the next sample.

play_chord.py:
    Example of how to generate and play chords using Python and NumPy.
    Can also play strings of notes, or can play notes from the keyboard.

podcopy:
    Copy podcasts (fetched with podget) to a mounted mp3 player or directory,
    or to an Android device via adb.
    Remove characters in filenames that would cause problems on vfat
    filesystems, and ensure filenames are unique and files aren't dups.

prettysoup:
    Prettyprint a BeautifulSoup object. Customizable, and avoids
    problems like BS4 prettify() adding spaces in the middle of words.

pyclip:
    Read the X clipboard.

pykey.py:
    Simulate keypresses under X. A simpler, Python version of
    Crikey, http://shallowsky.com/software/crikey/

pyplay.py:
    A class to play sounds asynchronously by calling aplay (or an app
    of your choice). Don't repeat a sound that's already playing.
    Used in the xchat script chatsounds.py.

pyruler:
    An X pixel ruler. Useful for measuring things like icon sizes.

pysync:
    Call rsync, but check first what would be changed, and save the
    password between the two calls.

python-cheatsheet.py:
    Cheatsheet and syntax reminders for useful Python features.

qpreso.py:
    A lightweight presentation program for displaying HTML slides.
    A Python3/Qt5/QtWebEngine version, since python-gtk-webkit
    (used for the older gpreso) is no longer supported.

randombg:
    Choose a random background (wallpaper) from a directory named based on
    current X resolution. So you can have different sets of backgrounds
    sized for laptop screen, external monitor etc.

randomline:
    Print a random line from a file. Useful for things like choosing
    a random wallpaper or random system beep tone.

readkey.py:
    Read a key press from the keyboard without waiting for a newline.
    For CLI programs: doesn't need X, tkintr, pygame or similar libs.

repo-pullpush:
    Modify a git repository, taking the existing URL, making that
    the pushurl and adding a passwordless pull URL alongside it.

rise_set_az.py:
    Find the times when the sun or moon will rise or set at a specific
    azimuth, within a specified phase range, from a specified location.

scrubjay:
    Demo of how to use a few different Twitter API.
    No UI as yet.
    Two variants: scrubjay-tweepy (tweepy) and scrubjay-p-t (python-twitter).

serio:
    A proof-of-concept serial terminal app in Python.
    Don't take this seriously; it's not meant as a real app (yet?)

shorturl:
    Use a URL shortening service to get a shorter URL.
    Can take input from the current X selection, and automatically
    select its output for pasting into a browser or Twitter window.

shorturl-gi3:
    shorturl ported to python3, GTK3 and GObject introspection (GI).
    Most useful as an example of how to use GI-GTK3.

sieve.py:
    Visualization of the Sieve of Eratosthenes, using Python curses.
    (Not very useful, but makes a good curses example.)

sinkto:
    Synchronize files in a list between two machines.
    Good for syncing updated scripts, dot files, documents,
    email folders etc. to a laptop when preparing for or returning
    from a trip, or just for keeping several machines in sync.

skyalignments.py:
    Starting from points in a GPX file, find all combinations of
    those points that line up with the rising or setting of the sun
    or full moon around solstices and equinoxes. Meant to show how
    easy it is for alignments to happen accidentally.

speedtestserver:
    A mini http server that can introduce delays or other glitches
    that are useful for testing http download clients.
    Unfortunately, it's only single-threaded which makes it
    not very useful except as an illustration of how to make
    a mini server in Python. Use delaytest.cgi for actual testing.

tee.py:
    A file-like class that can optionally send output to a log file.

termcolors:
    Display ANSI colors for the current terminal.

termsize:
    Set stty size to the size of the current terminal window,
    e.g. when logged in to an embedded Posix device over a serial line.

tklabelimage.py:
    Mini example of how to display text and images together in a label
    in TkInter, and of how to conditionally import Tk in python2 or 3.
    Doesn't do anything useful.

transimageviewer.py:
    A translucent image viewer (inheriting from imageviewer.py)
    that passes clicks and other events through to the window below.
    Useful for things like saving GPS waypoints from a map image.
    Also offers a rare example of how to use the X11 SHAPE extension
    from pygtk, including input shapes.

turtlefrac.py:
    Draw fractals (specifically a Sierpinski triangle)
    as an example of how to use Python turtle graphics.

tweet:
    Play birdsong from a specific bird. Requires ripped tracks from a
    bird song CD: for example, the Stokes, Cornell or Peterson collections.

qhtmlprint:
    Convert a set of HTML slides (e.g. in navigate.js) into PDF.
    For turning an HTML presentation into a PDF slide deck.
    Unfortunately the QtWebkit libraries this depends on
    seem to be abandoned; see qslide2pdf for a newer version.

qslide2pdf:
    Convert a set of HTML slides (e.g. in navigate.js) into PDF.
    For turning an HTML presentation into a PDF slide deck.
    Uses Qt5's QWebEngine and PyPDF2. We'll see how long that's supported.

qpdfview.py:
    A simple PDF viewer for Python-Qt5 using popplerqt5.

quickbrowse.py:
    A minimal browser in python-qtWebEngine. Fast and light,
    supposedly anonymous, no storage of cookies or other identifying
    information. Useful for things like viewing URLs from mutt or
    checking websites that don't work well with a Firefox/NoScript profile.
    Can be used standalone (ln -s /path/to/quickbrowse.py ~/bin/quickbrowse)
    and/or as a python module for derived browser-based programs.

quotekiosk.py:
    Display a series of plaintext quotes in a large, maybe fullscreen,
    window, as large as possible to fit in the window, changing the quote
    every so often.

qquotekiosk.py:
    Display a series of quotes or other content from HTML files,
    as large as possible to fit in the window, changing the quote
    every so often, using qpreso.py for the display window.
    Uses qpreso.py for the HTML display window.

urldownloader.py:
    Maintain a queue of URLs to download asynchronously to local files.

us-wars.py:
    Plot a Gantt chart of years of wars the US has participated in.
    Also serves as an example of a matplotlib Gantt chart.

vcalparse:
    Parse and print an icalendar/vcalendar/ICS file using python-vobject.

viewhtmlmail:
     Take an mbox HTML message (e.g. from mutt), split it using munpack,
     and rewrite it so it can be viewed in an external browser.

viewmailattachments:
     Show all attachments to an HTML message in a Firefox window,
     first running them through unoconv or other conversion programs
     as needed to convert MS Office formats to HTML or PDF.

vol:
    A simple python-gtk volume slider. Much simpler and smaller than
    alsamixergui.

waymaker:
    Take a file and of descriptions, multi-line and separated by blank lines,
    and turn it into a collection of GPX waypoints suitable for import into
    any mapping program (e.g. Osmand or PyTopo).

weather/cwop.py:
    Download and parse readings from Citizen Weather Observation Program
    stations.

weather/noaatemps.py:
    Display and plot weather means for a set of stations,
    by downloading NOAA data files.

weather/awsgoes.py:
    An example of how to fetch NOAA GOES-16 data from AWS anonymously,
    and plot it on a matplotlib Basemap map.
    Useful mainly as an example.

weather/weatherwin:
    Display a window showing temperature and today's forecast
    for several cities at once.

weborphans:
    Check a web site (perhaps localhost) against a local mirror,
    checking for broken links and orphaned files.

wikitable.py:
    Parse a data table from a wikipedia page, outputting CSV.

word2html:
    Convert .docx or .doc to prettyprinted HTML.
    Uses python-mammoth for docx, and either uniconv + python-mammoth
    or wvHtml for .doc. Uses BeautifulSoup for prettyprinting.

wordview:
    Convert a doc or docx file to html, and call a new firefox window on it.
    Predecessor to (and simpler than) viewmailattachments.

wpnet.py:
    A wrapper to make it easier to use wpa_cli to manage known wireless
    networks.

xbright:
    Adjust brightness of an X11 display up or down using xrandr.

xlsrd:
    Display an .xls spreadsheet as a formatted ASCII table, using
    the xlrd package to parse the spreadsheet.


--------
Testing:
--------

Only a few of the scripts have tests. Run tests with:

python3 -m unittest discover
