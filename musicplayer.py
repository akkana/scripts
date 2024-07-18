#! /usr/bin/env python

# A simple music player using pygame.

# Requirements: python-pygame python-id3
# Strongly recommended: python-mutagen
# which is used for MP3 song length and frequency, as well as ID3 tags;
# without mutagen, some songs may play too fast or too slowly.
#
# Copyright 2015.2019,2020,2021 by Akkana Peck:
# share and enjoy under the GPLv2 or later.

from __future__ import print_function

import sys, os
import time
import random
import re

# Gtk needs characters like & escaped in labels,
# but doesn't seem to provide a way to do that.
import html

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk, GLib

# Hide the silly "hello" message from pygame at import time.
# This supposedly will work with pygame > 1.9.4 but doesn't work yet.
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from pygame import mixer

try:
    import mutagen
    from mutagen.id3 import ID3
except:
    print("No mutagen, won't be able to check song length, adjust speeds")
    print("or read ID3 tags")


class MusicWin(Gtk.Window):
    LEFT_KEY = Gdk.KEY_Left
    RIGHT_KEY = Gdk.KEY_Right
    UP_KEY = Gdk.KEY_Up
    DOWN_KEY = Gdk.KEY_Down
    SPACE_KEY = Gdk.KEY_space
    Q_KEY = Gdk.KEY_q
    D_KEY = Gdk.KEY_d
    S_KEY = Gdk.KEY_s

    MAX_FILENAME_LEN = 90

    def __init__(self, init_songs, shuffle=None, backward=False):
        """
        init_songs: a list of songs, playlists (.m3u) and directories to play.
        shuffle: if True, will shuffle; if False, it won't.
                If shuffle is unset (None), default to True
                if init_songs has songs or playlists, else False.
        backward: play in reverse order (assuming shuffle is False)
        """

        super(MusicWin, self).__init__()

        self.songs = []
        self.song_ptr = -1

        self.cur_song_length = 0
        self.cur_song_length_str = '0'

        # GTK seems to have no way to set a scale without calling the callback.
        self.ignore_callbacks = False

        self.configdir = os.path.expanduser('~/.config/musicplayer')

        # Paths to try prepending to music or playlist filenames
        self.musicpaths = [ os.path.expanduser("~/Music"), self.configdir ]

        # Figure out whether shuffle mode should be set.
        # If shuffle mode wasn't passed in as an argument,
        # figure out whether it should be on.
        if shuffle is None:
            # First check the config file:
            configfile = os.path.join(self.configdir, "config")
            if os.path.exists(configfile):
                with open(configfile) as fp:
                    randomre = re.compile(r'^\s*random *= *([^ ]+)')
                    shufflere = re.compile(r'^\s*shuffle *= *([^ ]+)')
                    for line in fp:
                        if line.startswith('#'):
                            continue
                        m = shufflere.search(line)
                        if m:
                            val = m.group(1).strip().lower()
                            if val == "true" or val == '1':
                                shuffle = True
                            elif val == "false" or val == '0':
                                shuffle = False
                            else:
                                print("Config file error: '%s'" . line.strip())
                        break

        # Not set from the config file? Decide based on arguments.
        if shuffle is None:
            if init_songs:
                shuffle = False
            else:
                shuffle = True

        self.shuffle = shuffle

        self.backward = backward

        # It's also possible to have a list of songs and directories to avoid
        noplaylist = None
        self.noplayfile = None

        self.playlist = None

        # If no songs or playlists specified, look for favorites.m3u.
        if not init_songs:
            default_playlist = os.path.join(self.configdir, "favorites.m3u")
            if os.path.exists(default_playlist):
                init_songs = [ default_playlist ]
                noplaylist = True

        # If that's not there, look for ~/Music
        if not init_songs:
            default_playlist = os.path.expanduser("~/Music")
            if os.path.exists(default_playlist):
                init_songs = [ default_playlist ]
                noplaylist = True

        # Still nothing?
        if not init_songs:
            print("No songs specified and no ~/.config/musicplayer or ~/Music")
            sys.exit(1)

        if noplaylist:    # it might have been set to True, above
            self.noplayfile = os.path.join(self.configdir, "noplay.m3u")
            if os.path.exists(self.noplayfile):
                noplaylist = self.noplayfile
            else:
                noplaylist = None

        # If playing only a single playlist, record that as self.playlistfile
        # so d, - or DEL can remove songs from it.
        if len(init_songs) == 1 and init_songs[0].lower().endswith(".m3u"):
            self.playlistfile = init_songs[0]

        # Build up the song list.
        self.expand_songs_and_directories(init_songs, noplaylist=noplaylist)

        # Are we stopped, paused or playing?
        MusicWin.STOPPED = 0
        MusicWin.PAUSED = 1
        MusicWin.PLAYING = 2
        self.play_state = MusicWin.PLAYING

        # The amount to skip by when the user skips:
        self.skip_sec = 20
        # Alas, the mixer doesn't reset its time limits when skipping,
        # so we have to remember that.
        self.skipped_seconds = 0

        #############################
        # The window and UI:
        mainbox = Gtk.VBox(spacing=8)
        self.add(mainbox)

        def add_class(obj, newclass):
            entry_style_context = obj.get_style_context()
            entry_style_context.add_class(newclass)

        buttonbox = Gtk.ButtonBox(spacing=4)
        buttonbox.set_name("buttonbox")
        mainbox.pack_end(buttonbox, False, False, 0)

        prev_btn = Gtk.Button(label="<<")
        prev_btn.set_tooltip_text("Previous song")
        prev_btn.connect("clicked", self.prev_song);
        add_class(prev_btn, "button")
        buttonbox.add(prev_btn)

        restart_btn = Gtk.Button(label="|<")
        restart_btn.set_tooltip_text("Restart song")
        restart_btn.connect("clicked", self.restart);
        add_class(restart_btn, "button")
        buttonbox.add(restart_btn)

        back_btn = Gtk.Button(label="<")
        back_btn.set_tooltip_text("Skip back 10 sec")
        back_btn.connect("clicked", self.skip_back);
        add_class(back_btn, "button")
        buttonbox.add(back_btn)

        self.pause_btn = Gtk.Button(label="||")
        self.pause_btn.set_tooltip_text("Pause")
        self.pause_btn.connect("clicked", self.pause);
        add_class(self.pause_btn, "button")
        buttonbox.add(self.pause_btn)

        self.stop_btn = Gtk.Button(label=u"\u25A0")
        self.stop_btn.set_tooltip_text("Stop")
        self.stop_btn.connect("clicked", self.stop);
        add_class(self.stop_btn, "button")
        buttonbox.add(self.stop_btn)

        fwd_btn = Gtk.Button(label=">")
        fwd_btn.connect("clicked", self.skip_fwd);
        fwd_btn.set_tooltip_text("Skip forward 10 sec")
        add_class(fwd_btn, "button")
        buttonbox.add(fwd_btn)

        next_btn = Gtk.Button(label=">>")
        next_btn.set_tooltip_text("Next song")
        next_btn.connect("clicked", self.next_song);
        add_class(next_btn, "button")
        buttonbox.add(next_btn)

        # Assorted info, like the shuffle button and progress indicator:
        views = Gtk.HBox(spacing=4)
        # views.padding = 8 So frustrating that we can't set this in general!
        mainbox.pack_end(views, False, False, 0)

        self.time_label = Gtk.Label()
        views.pack_start(self.time_label, fill=False, expand=False, padding=8)

        # A slider for an adjustable progress indicator
        self.progress_adj = Gtk.Adjustment(value=0, lower=0, upper=100,
                                           step_increment=5,
                                           page_increment=10,
                                           page_size=0)
        self.progress_hscale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                         adjustment=self.progress_adj,
                                         draw_value=False, digits=0)
        self.progress_hscale.connect("value-changed", self.prog_scale_moved)
        views.pack_start(self.progress_hscale,
                         fill=True, expand=True, padding=8)

        shuffleBtn = Gtk.ToggleButton(label="Shuffle")
        shuffleBtn.set_active(self.shuffle)
        shuffleBtn.connect("toggled", self.toggle_shuffle);
        views.pack_end(shuffleBtn, fill=True, expand=False, padding=8)

        # The content areas for the song filename, title and artist:
        # you might think HTML/CSS markup would let you put these all
        # together in one label, since isn't that the point of html?
        # but you'd be wrong:
        # GTK doesn't let you add things like <span id=''> inside a label.
        # Set the initial label to a width that will allow room for
        # the max number of characters; a string of spaces doesn't do it,
        # a string of all m is a little too wide.
        self.filename_labl = Gtk.Label(label='o' * self.MAX_FILENAME_LEN)

        # The label has this function but it doesn't actually limit anything.
        # limit it in the update function instead.
        # self.filename_labl.set_max_width_chars(90)
        # self.filename_labl.set_use_markup(True)
        # self.filename_labl.set_line_wrap(True)
        # Right-justify the filename to prefer the basename.
        # This of course is pointless since GTK can't limit the label size
        # and just resizes the window any time the text gets longer.
        # So, again, handle this in the update function.
        self.filename_labl.set_justify(Gtk.Justification.CENTER)
        self.filename_labl.set_name("filename")
        mainbox.pack_start(self.filename_labl, False, False, 0)

        self.title_labl = Gtk.Label()
        self.title_labl.set_use_markup(True)
        self.title_labl.set_line_wrap(True)
        self.title_labl.set_justify(Gtk.Justification.CENTER)
        self.title_labl.set_name("title")
        mainbox.pack_start(self.title_labl, False, False, 0)

        self.artist_labl = Gtk.Label()
        self.artist_labl.set_use_markup(True)
        self.artist_labl.set_line_wrap(True)
        self.artist_labl.set_justify(Gtk.Justification.CENTER)
        self.artist_labl.set_name("artist")
        mainbox.pack_start(self.artist_labl, False, False, 0)

        # Style the whole window:
        css = b'''
#maincontent { padding: 0em; margin: 0em; border: 0em; }
#filename { font-style: italic; }
#title { font-weight: bold; font-size: 2em; }
#artist { font-size: 1.5em; }
button { border-radius: 15px; border-width: 2px; border-style: outset; }
button:hover { background: #dff; border-color: #8bb; }
'''
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        context = Gtk.StyleContext()
        screen = Gdk.Screen.get_default()
        context.add_provider_for_screen(screen, css_provider,
                                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Add events we need to listen to:
        self.connect("key-press-event", self.key_press_event)

        self.add_events(Gdk.EventMask.SCROLL_MASK)
        self.connect("scroll-event", self.scroll_event)

        # Try to set a maximum size.
        # In GTK3 this also sets initial size, and it's too big.
        # self.set_size_request(550, 225)

        mixer.init()

    @staticmethod
    def playok(songpath, noplaylist=None):
        """Is it ok to play this song? It's not prohibited by the noplaylist?
        """
        if not noplaylist:
            return True
        for badsong in noplaylist:
            if badsong in songpath:
                return False
        return True

    def add_songs_from_dir(self, d, noplaylist=None):
        # XXX Recursively crawl the directory and add every song in it.
        for root, dirs, files in os.walk(d):
            for filename in files:
                if '.' in filename:
                    songpath = os.path.join(root, filename)
                    if self.playok(songpath):
                        self.songs.append(songpath)

    def expand_songs_and_directories(self, slist, noplaylist=None):
        """slist is a list of song files and directories.
           noplaylist (optional) is a list of songs and directories
           NOT to include.
        """
        if type(slist) is str:
            slist = [slist]

        # First, if noplaylist is specified, expand that:
        if noplaylist:
            with open(noplaylist) as fp:
                noplaylist = []
                for line in fp:
                    noplaylist.append(line.strip())

        for s in slist:
            if os.path.isdir(s):
                self.add_songs_from_dir(s, noplaylist=noplaylist)

            elif s.lower().endswith('.m3u'):
                if os.path.exists(s):
                    self.add_songs_in_playlist(s, noplaylist)
                elif os.path.exists(os.path.join(self.configdir, s)):
                    self.add_songs_in_playlist(os.path.join(self.configdir, s))
                else:
                    print(s, ": No such playlist")
            else:
                if os.path.exists(s) and self.playok(s, noplaylist):
                    self.songs.append(s)
                else:
                    print(s, ": No such file")

        # random.shuffle() doesn't produce a very random list,
        # and in any case it's deprecated and doesn't seem to have
        # a replacement.
        # XXX It would be nice to keep the original list,
        # to allow toggling between shuffle and sequential mode
        # at runtime.
        if self.shuffle:
            shuffled = []
            while self.songs:
                shuffled.append(
                    self.songs.pop(random.randrange(len(self.songs))))

            self.songs = shuffled

        elif self.backward:
            self.songs.reverse()

        # Even if self.shuffle isn't currently set,
        # it might be toggled on later, so be prepared.
        random.seed(os.getpid())

    def add_songs_in_playlist(self, playlist, noplaylist=None):
        with open(playlist) as m3ufile:
            for line in m3ufile:
                line = line.strip()
                if not line:
                    continue
                if os.path.isdir(line):
                    self.add_songs_from_dir(line, noplaylist)
                    continue
                if os.path.exists(line) and self.playok(line, noplaylist):
                    self.songs.append(line)
                    continue

                for path in self.musicpaths:
                    linepath = os.path.join(path, line)
                    if os.path.isdir(linepath):
                        self.add_songs_from_dir(linepath, noplaylist)
                        break
                    if os.path.exists(linepath) and \
                       self.playok(linepath, noplaylist):
                        self.songs.append(linepath)
                        break

    def run(self):
        if not self.songs:
            print("No songs to play!")
            return

        self.connect("delete_event", self.quit)
        self.connect("destroy", self.quit)
        # self.winsig = self.connect("configure_event", self.configure_event)

        self.show_all()

        # set a timeout
        GLib.timeout_add(500, self.timer_func)

        Gtk.main()

    def quit(self, w=None, data=None):
        # Save playlist? But we really shouldn't need to,
        # since we saved it after anything that would change it.
        # self.save_playlist()
        Gtk.main_quit()

    def restart(self, w=None):
        # mixer.music.rewind() loses all track of the current position.
        # So instead, just stop and start again.
        self.skipped_seconds = 0
        self.stop()
        self.song_ptr = (self.song_ptr - 1) % len(self.songs)
        self.play_state = MusicWin.PLAYING

    def set_scale_slider(self, secs):
        self.ignore_callbacks = True
        self.progress_hscale.set_value(secs)
        self.ignore_callbacks = False

    def pause(self, w=None):
        if self.play_state == MusicWin.PLAYING:
            mixer.music.pause()
            self.pause_btn.set_label(u"||")
            self.pause_btn.set_tooltip_text("Un-pause")
            self.pause_btn.set_sensitive(True)

            self.stop_btn.set_label(u"\u25B6") # black right-pointing triangle
            self.stop_btn.set_tooltip_text("Play")
            self.stop_btn.set_sensitive(True)

            self.play_state = MusicWin.PAUSED

        elif self.play_state == MusicWin.PAUSED:
            mixer.music.unpause()
            self.pause_btn.set_label('||')
            self.pause_btn.set_tooltip_text("Pause")
            self.pause_btn.set_sensitive(True)

            self.stop_btn.set_sensitive(False)

            self.play_state = MusicWin.PLAYING
        # else must be MusicWin.STOPPED. Do nothing, keep it there.

    def stop(self, w=None):
        if self.play_state == MusicWin.PLAYING:
            mixer.music.stop()
            self.stop_btn.set_label(u"\u25B6") # black right-pointing triangle
            self.stop_btn.set_tooltip_text("Play")
            self.stop_btn.set_sensitive(True)

            self.pause_btn.set_label('||')
            self.pause_btn.set_tooltip_text("Pause")
            self.pause_btn.set_sensitive(False)

            self.play_state = MusicWin.STOPPED
            self.skipped_seconds = 0
            self.set_time_label(0)
            self.set_scale_slider(0)

        else:    # Must be stopped or paused already. Play from beginning.
            self.stop_btn.set_label(u"\u25A0") # black square
            self.stop_btn.set_tooltip_text("Play")

            self.pause_btn.set_label('||')
            self.pause_btn.set_tooltip_text("Pause")
            self.pause_btn.set_sensitive(True)

            self.play_state = MusicWin.PLAYING
            self.skipped_seconds = 0
            self.set_scale_slider(0)
            self.set_time_label(0)
            mixer.music.play()

    def toggle_shuffle(self, w):
        self.shuffle = w.get_active()
        cursong = self.songs[self.song_ptr]
        if self.shuffle:
            random.shuffle(self.songs)
        else:
            self.songs.sort(reverse=self.backward)

        # Now re-find the song we were playing:
        try:
            self.song_ptr = self.songs.index(cursong)
        except:
            print("Current song doesn't seem to be in the list any more!")
            print(cursong)
            self.song_ptr = 0

    def next_song(self, w=None):
        self.stop()
        self.play_state = MusicWin.PLAYING

    def prev_song(self, w=None):
        self.song_ptr = (self.song_ptr - 2) % len(self.songs)
        self.stop()
        self.play_state = MusicWin.PLAYING

    def skip(self, sec):
        pos = mixer.music.get_pos() / 1000.0 + self.skipped_seconds
        # get_pos returns milliseconds.
        # Supposedly the position argument of play() takes seconds.
        pos += sec
        if pos < 0: pos = 0.
        self.skipped_seconds = pos
        mixer.music.play(0, pos)

    def prog_scale_moved(self, event):
        if self.ignore_callbacks:
            return

        pos = self.progress_hscale.get_value()
        self.set_time_label(pos)
        self.skipped_seconds = pos
        mixer.music.play(0, pos)

    def skip_fwd(self, w=None):
        self.skip(20)

    def skip_back(self, w=None):
        # self.skip(-10000)
        self.skip(-20)

    def volume_change(self, delta):
        vol = mixer.music.get_volume()
        mixer.music.set_volume(vol + delta)

    def volume_up(self, w=None):
        self.volume_change(.1)

    def volume_down(self, w=None):
        self.volume_change(-.1)

    def delete_song(self, from_disk):
        # If using a noplayfile, just add it to that and skip
        # to the next song, if not deleting from disk.
        if self.noplayfile:
            with open(self.noplayfile, "a") as fp:
                print(self.songs[self.song_ptr], file=fp)
                print("Adding", self.songs[self.song_ptr],
                      "to no-play list")
            if not from_disk:
                # skip to the next song.
                mixer.music.stop()
                return

        if from_disk:
            delstr = "Delete song from disk PERMANENTLY?"
        elif self.playlist:
            delstr = "Delete song from playlist?"
        else:
            print("""Deleting a song from the playlist requires either
using a no-play file or a single playlist""")
            return

        dialog = Gtk.MessageDialog(transient_for=self, flags=0,
                                   message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text=delstr)
        dialog.set_default_response(Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:

            cur_song = self.songs[self.song_ptr]
            del self.songs[self.song_ptr]
            self.song_ptr = (self.song_ptr - 1) % len(self.songs)

            if self.playlistfile:
                self.save_playlist()

            if from_disk:
                os.remove(cur_song)

            # Either way, skip to the next song.
            mixer.music.stop()

    def save_playlist(self):
        """Save the current playlist."""
        if not self.playlistfile:
            print("No playlist to save to!")
            return

        if not os.path.exists(self.configdir):
            os.makedirs(self.configdir)

        if os.path.exists(self.playlistfile):
            os.rename(self.playlistfile, self.playlistfile + '.bak')

        fp = open(self.playlistfile, "w")
        newlist = self.songs[:]
        newlist.sort(reverse=self.backward)
        for song in newlist:
            fp.write(song + '\n')
        fp.close()

    def set_label_text(self, text, labl):
        """Use for setting the filename and title labels.
           Limit content to a fixed number of characters.
        """
        if len(text) > self.MAX_FILENAME_LEN:
            text = text[:self.MAX_FILENAME_LEN]
        labl.set_label(html.escape(text))

    def update_content(self):
        has_title = False
        has_artist = False

        # self.filename_labl.set_label('<span class="headline">Headline</span>'
        #                              '<span class="normal">Normal text</span>')

        # Limit the filename size, since GTK doesn't seem able to do that.
        fname_len = len(self.songs[self.song_ptr])
        if fname_len > self.MAX_FILENAME_LEN:
            fname = self.songs[self.song_ptr][fname_len-self.MAX_FILENAME_LEN:]
        else:
            fname = self.songs[self.song_ptr]
        self.set_label_text(fname, self.filename_labl)

        try:
            id3info = ID3(self.songs[self.song_ptr])
            # If encoded in other than the system encoding, these
            # may display incorrectly in the UI. So recode them.

        except:
            id3info = {}

        # The keys in mutagen.ID3 don't seem to be documented anywhere!
        # This is empirical and will probably break at some point.

        try:
            title = id3info['TIT2'].text[0]     # TITLE
        except:
            title = os.path.splitext(os.path.basename(
                self.songs[self.song_ptr]).replace("_", " "))[0]
        self.set_label_text(title, self.title_labl)

        try:
            artist = id3info['TPE1'].text[0]    # ARTIST
        except:
            artist = "-"
        self.set_label_text(artist, self.artist_labl)


    def key_press_event(self, widget, event):
        if event.keyval == MusicWin.Q_KEY and \
           event.state | Gdk.ModifierType.CONTROL_MASK:
            # Can't just check for == CONTROL_MASK because GTK randomly
            # sets other bits like GDK_MOD2_MASK for no apparent reason
            self.quit()
        elif event.keyval == MusicWin.LEFT_KEY:
            self.prev_song()
        elif event.keyval == MusicWin.RIGHT_KEY:
            self.next_song()
        elif event.keyval == MusicWin.UP_KEY:
            self.volume_up()
        elif event.keyval == MusicWin.DOWN_KEY:
            self.volume_down()
        elif event.keyval == MusicWin.SPACE_KEY:
            self.pause()
        elif event.string == '.':
            self.stop()
        elif event.string == '0':
            self.restart()

        # d means add the song to CONFIGDIR/notfavorites.m3u
        # so it won't be played by default.
        # ctrl-d actually deletes the song from disk.
        elif event.keyval == MusicWin.D_KEY:
            if event.state | Gdk.ModifierType.CONTROL_MASK:
                self.delete_song(True)
            else:
                self.delete_song(False)
        # Some other keys that add to notfavorites.m3u: - and DEL
        elif event.keyval == Gdk.KEY_Delete or event.string == '-':
            self.delete_song(False)

        elif event.keyval == MusicWin.S_KEY and \
           event.state | Gdk.ModifierType.CONTROL_MASK:
            self.save_playlist()

        return True

    def scroll_event(self, widget, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self.volume_up()
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.volume_down()

    def sec_to_str(self, sec):
        """Convert seconds (int) to h:m:s (string)"""
        s = sec % 60
        m = int(sec / 60)
        h = int(sec / 3600)
        if h:
            return '%2d:%02d:%02d' % (h, m, s)
        else:
            return '%2d:%02d' % (m, s)

    def set_time_label(self, secs):
        self.time_label.set_label(self.sec_to_str(secs)
                                  + " / " + self.cur_song_length_str)

    def timer_func(self):
        """The timer func is what does the actual playing of songs,
           as well as skipping to the next or previous song.
        """
        # If we're stopped, don't change anything.
        if self.play_state == MusicWin.STOPPED or \
           self.play_state == MusicWin.PAUSED:
            return True

        # Are we still playing the same song?
        if mixer.music.get_busy():
            # This is only approximate.
            secs = self.skipped_seconds + (mixer.music.get_pos()/1000)
            self.set_time_label(secs)
            self.set_scale_slider(int(secs))
            return True

        # Else time to play the next song.
        self.skipped_seconds = 0
        self.set_scale_slider(0)
        self.song_ptr = (self.song_ptr + 1) % len(self.songs)

        while not os.path.exists(self.songs[self.song_ptr]):
            print(self.songs[self.song_ptr], "doesn't exist!")
            del self.songs[self.song_ptr]
            # self.song_ptr = (self.song_ptr - 1) % len(self.songs)

        self.update_content()

        # Try to get the length and sample rate
        songinfo = None
        try:
            songinfo = mutagen.File(self.songs[self.song_ptr]).info
        except Exception as e:
            print("Didn't recognize file type of", self.songs[self.song_ptr],
                  ":", e)
            songinfo = None

        if songinfo:
            self.cur_song_length = songinfo.length
            self.cur_song_length_str = self.sec_to_str(self.cur_song_length)

            # Show the length on the hscale slider
            self.progress_hscale.set_range(0, self.cur_song_length)

            mixer.quit()
            mixer.init(frequency=songinfo.sample_rate)

        try:
            # Then load and play the song.
            mixer.music.load(self.songs[self.song_ptr])
            mixer.music.play()

            # Make sure the buttons are sane:
            self.pause_btn.set_label('||')
            self.stop_btn.set_label(u"\u25A0") # black square

        except Exception as e:
            print("Can't play", self.songs[self.song_ptr], ':', str(e))
            del self.songs[self.song_ptr]
            if not self.songs:
                sys.exit(1)
            self.song_ptr = (self.song_ptr - 1) % len(self.songs)
        return True


if __name__ == '__main__':
    rc = os.fork()
    if rc:
        sys.exit(0)

    args = sys.argv[1:]
    shuffle = None
    backward = False
    if args:
        if args[0] == '-h' or args[0] == '--help':
            print("Usage: %s [-s|--shuffle] [-S|--sequential] [-b|--backward]" % os.path.basename(sys.argv[0]))
            sys.exit(0)

        if args[0] == '-r' or args[0] == 's' or args[0] == '--shuffle':
            shuffle = True
            args = args[1:]

        elif args[0] == '-S' or args[0] == '--sequential':
            shuffle = False
            args = args[1:]

        elif args[0] == '-b' or args[0] == '--backward':
            backward = True
            shuffle = False
            args = args[1:]

    win = MusicWin(args, shuffle=shuffle, backward=backward)
    win.run()

