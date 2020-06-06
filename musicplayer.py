#! /usr/bin/env python

# A simple music player using pygame.
# Requirements: python-pygame python-id3
# Strongly recommended: python-mutagen
# (uses mutagen for MP3 song length and frequency; without it,
# some songs may play too fast or too slowly).
#
# Copyright 2015.2019,2020 by Akkana Peck: share and enjoy under the GPLv2 or later.

from __future__ import print_function

import sys, os
import time
import random
import re

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk, GLib

# Hide the silly "hello" message from pygame at import time.
# This supposedly will work with pygame > 1.9.4 but doesn't work yet.
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from pygame import mixer

import cgi

try:
    import ID3
except:
    pass

try:
    from mutagen.mp3 import MP3
except:
    print("No mutagen, won't be able to check song length or adjust speeds")

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

    def __init__(self, init_songs, random=None, backward=False):
        super(MusicWin, self).__init__()

        self.songs = []
        self.song_ptr = -1

        self.cur_song_length = 0

        self.configdir = os.path.expanduser('~/.config/musicplayer')

        # If no songs or playlists specified, play from our favorites playlist.
        if not init_songs:
            self.playlist = os.path.join(self.configdir, "favorites.m3u")
            print("Playing favorites")
            init_songs = [ self.playlist ]
        # Did the user specify one single playlist?
        elif len(init_songs) == 1 \
           and init_songs[-1].endswith('.m3u'):
            self.playlist = os.path.join(self.configdir,
                                         os.path.basename(init_songs[-1]))
        else:
            self.playlist = os.path.join(self.configdir, 'playlist.m3u')

        # Right now, random is the only thing that can be specified
        # in the config file.
        if random is None:
            configfile = os.path.join(self.configdir, "config")
            if os.path.exists(configfile):
                fp = open(configfile)
                randomre = re.compile('random *= *([^ ]+)')
                for line in fp:
                    if line.startswith('#'):
                        continue
                    m = randomre.search(line)
                    if m:
                        val = m.group(1).strip().lower()
                        if val == "true" or val == '1':
                            self.random = True
                        elif val == "false" or val == '0':
                            self.random = False
                        else:
                            print("Config file error: '%s'" . line.strip())
                    break
                fp.close()

            else:
                # If there's no config file, default to not random.
                self.random = False
        else:
            self.random = random

        self.backward = backward

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

        # Assorted info, like the random button and progress indicator:
        views = Gtk.HBox(spacing=4)
        # views.padding = 8 So frustrating that we can't set this in general!
        mainbox.pack_end(views, False, False, 0)
        self.time_label = Gtk.Label()

        views.pack_start(self.time_label, False, False, 8)

        randomBtn = Gtk.ToggleButton(label="Shuffle")
        randomBtn.set_active(self.random)
        randomBtn.connect("toggled", self.toggle_random);
        views.pack_end(randomBtn, fill=True, expand=False, padding=8)

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

        # Done with UI! Now we can build up the song list.
        self.add_songs_and_directories(init_songs)

        mixer.init()

    def add_songs_and_directories(self, slist):
        for s in slist:
            if os.path.isdir(s):
                # XXX Recursively crawl the directory and add every song in it.
                for root, dirs, files in os.walk(s):
                    for filename in files:
                        if '.' in filename:
                            self.songs.append(os.path.join(root, filename))
            elif s.endswith('.m3u'):
                if os.path.exists(s):
                    self.add_songs_in_playlist(s)
                elif os.path.exists(os.path.join(self.configdir, s)):
                    self.add_songs_in_playlist(os.path.join(self.configdir, s))
                else:
                    print(s, ": No such playlist")
            else:
                if os.path.exists(s):
                    self.songs.append(s)
                else:
                    print(s, ": No such file")

        # Play music in random order:
        random.seed(os.getpid())
        if self.random:
            random.shuffle(self.songs)
        else:
            self.songs.sort(reverse=self.backward)

    def add_songs_in_playlist(self, playlist):
        path = os.path.split(playlist)[0]
        with open(playlist) as m3ufile:
            for line in m3ufile:
                self.songs.append(os.path.join(path, line.strip()))

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

    def restart(self, w):
        # mixer.music.rewind() loses all track of the current position.
        # So instead, just stop and start again.
        self.skipped_seconds = 0
        self.stop()
        self.song_ptr = (self.song_ptr - 1) % len(self.songs)
        self.play_state = MusicWin.PLAYING

    def pause(self, w=None):
        if self.play_state == MusicWin.PLAYING:
            mixer.music.pause()
            self.pause_btn.set_label(u"\u25B6") # black right-pointing triangle
            self.pause_btn.set_tooltip_text("Un-pause")
            self.play_state = MusicWin.PAUSED
        elif self.play_state == MusicWin.PAUSED:
            mixer.music.unpause()
            self.pause_btn.set_label('||')
            self.pause_btn.set_tooltip_text("Pause")
            self.play_state = MusicWin.PLAYING
        # else must be MusicWin.STOPPED. Nothing to do.

    def stop(self, w=None):
        if self.play_state in [MusicWin.PLAYING, MusicWin.PAUSED]:
            mixer.music.stop()
            self.stop_btn.set_label(u"\u25B6") # black right-pointing triangle
            self.stop_btn.set_tooltip_text("Play")
            self.play_state = MusicWin.STOPPED
            self.skipped_seconds = 0
            self.time_label.set_label("0")
        else:    # Must be stopped already. Play something.
            mixer.music.play()
            self.stop_btn.set_label(u"\u25A0") # black square
            self.stop_btn.set_tooltip_text("Play")
            self.play_state = MusicWin.PLAYING

    def toggle_random(self, w):
        self.random = w.get_active()
        cursong = self.songs[self.song_ptr]
        if self.random:
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
        mixer.music.stop()
        self.play_state = MusicWin.PLAYING

    def prev_song(self, w=None):
        self.song_ptr = (self.song_ptr - 2) % len(self.songs)
        mixer.music.stop()
        self.play_state = MusicWin.PLAYING

    def skip(self, sec):
        pos = mixer.music.get_pos() / 1000.0 + self.skipped_seconds
        # get_pos returns milliseconds.
        # Supposedly the position argument of play() takes seconds.
        pos += sec
        if pos < 0: pos = 0.
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
        if from_disk:
            delstr = "Delete song from disk PERMANENTLY?"
        else:
            delstr = "Delete song from playlist?"
        dialog = Gtk.MessageDialog(self,
                                   Gtk.DIALOG_DESTROY_WITH_PARENT,
                                   Gtk.MESSAGE_QUESTION,
                                   Gtk.BUTTONS_OK_CANCEL,
                                   delstr)
        dialog.set_default_response(Gtk.RESPONSE_OK)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.RESPONSE_OK:
            cur_song = self.songs[self.song_ptr]
            del self.songs[self.song_ptr]
            self.song_ptr = (self.song_ptr - 1) % len(self.songs)
            self.save_playlist()
            if from_disk:
                os.remove(cur_song)

            # Either way, skip to the next song.
            mixer.music.stop()

    def delete_song_from_playlist(self):
        self.delete_song(False)

    def delete_song_from_disk(self):
        self.delete_song(True)

    def save_playlist(self):
        """Save the current playlist."""
        if not self.playlist:
            print("No playlist to save to!")
            return

        if not os.path.exists(self.configdir):
            os.makedirs(self.configdir)

        if os.path.exists(self.playlist):
            os.rename(self.playlist, self.playlist + '.bak')

        fp = open(self.playlist, "w")
        newlist = self.songs[:]
        newlist.sort(reverse=self.backward)
        for song in newlist:
            fp.write(song + '\n')
        fp.close()

    def update_content(self):
        has_title = False
        has_artist = False

        self.filename_labl.set_label('<span class="headline">Headline</span>'
                                     '<span class="normal">Normal text</span>')
        # Limit the filename size, since GTK doesn't seem able to do that.
        fname_len = len(self.songs[self.song_ptr])
        if fname_len > self.MAX_FILENAME_LEN:
            fname = self.songs[self.song_ptr][fname_len-self.MAX_FILENAME_LEN:]
        else:
            fname = self.songs[self.song_ptr]
        self.filename_labl.set_label(fname)

        try:
            id3info = ID3.ID3(self.songs[self.song_ptr])
        except:
            self.title_labl.set_label(os.path.splitext(
                os.path.basename(self.songs[self.song_ptr]))[0])
            self.artist_labl.set_label('-')
            return

        # for k, v in id3info.items():
        #     if k == "ARTIST":
        #         has_artist = True
        #     elif k == "TITLE":
        #         has_title = True
        #     text += '\n' + k + ' : ' + v

        try:
            self.title_labl.set_label(unicode(cgi.escape(id3info['TITLE']),
                                                         'utf-8',
                                                         errors='replace'))
        except KeyError:
            self.title_labl.set_label(os.path.basename(self.songs[self.song_ptr]))
        try:
            self.artist_labl.set_label(cgi.escape(id3info['ARTIST']))
        except KeyError:
            self.artist_labl.set_label('-')

    def key_press_event(self, widget, event):
        if event.keyval == MusicWin.Q_KEY and \
           event.state == Gdk.ModifierType.CONTROL_MASK:
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

        # d means delete from the current playlist;
        # ctrl-d actually deletes the song from disk.
        elif event.keyval == MusicWin.D_KEY:
            if event.state == Gdk.ModifierType.CONTROL_MASK:
                self.delete_song_from_disk()
            else:
                self.delete_song_from_playlist()

        elif event.keyval == MusicWin.S_KEY and \
           event.state == Gdk.ModifierType.CONTROL_MASK:
            print("Saving playlist")
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
            return '%d:%02d:%02d' % (h, m, s)
        else:
            return '%d:%02d' % (m, s)

    def timer_func(self):
        """The timer func is what does the actual playing of songs."""
        # If we're stopped, don't change anything.
        if self.play_state == MusicWin.STOPPED:
            return True

        # Are we still playing the same song?
        if mixer.music.get_busy():
            # This sadly still isn't right. Sigh.
            self.time_label.set_label(self.sec_to_str(self.skipped_seconds +
                                                      (mixer.music.get_pos()
                                                       /1000))
                                      + " / " + self.cur_song_length_str)
            return True

        # Else time to play the next song.
        self.skipped_seconds = 0
        self.song_ptr = (self.song_ptr + 1) % len(self.songs)

        while not os.path.exists(self.songs[self.song_ptr]):
            print(self.songs[self.song_ptr], "doesn't exist!")
            del self.songs[self.song_ptr]
            # self.song_ptr = (self.song_ptr - 1) % len(self.songs)

        self.update_content()

        # Get the length:
        try:
            mp3info = MP3(self.songs[self.song_ptr])
            self.cur_song_length = mp3info.info.length
            self.cur_song_length_str = self.sec_to_str(self.cur_song_length)
        except:
            self.cur_song_length = 0
            self.cur_song_length_str = '?'

        try:
            # First try to adjust the speed. This used to happen
            # automatically, but now, some songs will play too fast
            # or too slowly.
            # This relies on mutagen, so it won't happen if it's not available.
            try:
                mp3 = MP3(self.songs[self.song_ptr])
                # print("New frequency is", mp3.info.sample_rate)
                mixer.quit()
                mixer.init(frequency=mp3.info.sample_rate)
            except NameError:
                # print("Couldn't adjust speed, maybe mutagen isn't available?")
                pass

            # Then load and play the song.
            mixer.music.load(self.songs[self.song_ptr])
            mixer.music.play()

            # Make sure the buttons are sane:
            self.pause_btn.set_label('||')
            self.stop_btn.set_label(u"\u25A0") # black square
        except Exception as e:
            print("Can't play", self.songs[self.song_ptr], ':', str(e))
            del self.songs[self.song_ptr]
            self.song_ptr = (self.song_ptr - 1) % len(self.songs)
        return True

if __name__ == '__main__':
    rc = os.fork()
    if not rc:
        args = sys.argv[1:]
        rand = None
        backward = False
        if args:
            if args[0] in ['-r', '--random']:
                rand = True
                args = args[1:]
            elif args[0] in ['-s', '--sequential']:
                rand = False
                args = args[1:]
            elif args[0] in ['-b', '--backward']:
                backward = True
                rand = False
                args = args[1:]

        win = MusicWin(args, random=rand, backward=backward)
        win.run()
    else:
        sys.exit(0)

