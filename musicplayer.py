#! /usr/bin/env python

import sys, os
import time
import random
import re

from pygame import mixer
import ID3
import cgi
from mutagen.mp3 import MP3

import gtk, gobject

class MusicWin(gtk.Window) :
    def __init__(self, init_songs, random=None, backward=False):
        super(MusicWin, self).__init__()

        self.songs = []
        self.song_ptr = -1

        self.cur_song_length = 0

        self.configdir = os.path.expanduser('~/.config/musicplayer')

        # If no songs or playlists specified, play from our favorites playlist.
        if not init_songs:
            self.playlist = os.path.join(self.configdir, "favorites.m3u")
            print "Playing favorites"
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
        if random == None:
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
                            print "Config file error: '%s'" . line.strip()
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

        # The window and UI:
        mainbox = gtk.VBox(spacing=8)
        self.add(mainbox)

        buttonbox = gtk.HBox(spacing=4)
        mainbox.pack_end(buttonbox, expand=False)

        prev_btn = gtk.Button("<<")
        prev_btn.set_tooltip_text("Previous song")
        prev_btn.connect("clicked", self.prev_song);
        buttonbox.add(prev_btn)

        restart_btn = gtk.Button("|<")
        restart_btn.set_tooltip_text("Restart song")
        restart_btn.connect("clicked", self.restart);
        buttonbox.add(restart_btn)

        back_btn = gtk.Button("<")
        back_btn.set_tooltip_text("Skip back 10 sec")
        back_btn.connect("clicked", self.skip_back);
        buttonbox.add(back_btn)

        self.pause_btn = gtk.Button("||")
        self.pause_btn.set_tooltip_text("Pause")
        self.pause_btn.connect("clicked", self.pause);
        buttonbox.add(self.pause_btn)

        self.stop_btn = gtk.Button(u"\u25A0")
        self.stop_btn.set_tooltip_text("Stop")
        self.stop_btn.connect("clicked", self.stop);
        buttonbox.add(self.stop_btn)

        fwd_btn = gtk.Button(">")
        fwd_btn.connect("clicked", self.skip_fwd);
        fwd_btn.set_tooltip_text("Skip forward 10 sec")
        buttonbox.add(fwd_btn)

        next_btn = gtk.Button(">>")
        next_btn.set_tooltip_text("Next song")
        next_btn.connect("clicked", self.next_song);
        buttonbox.add(next_btn)

        # Assorted info, like the random button and progress indicator:
        views = gtk.HBox(spacing=4)
        # views.padding = 8 So frustrating that we can't set this in general!
        mainbox.pack_end(views, expand=False)
        self.time_label = gtk.Label()

        views.pack_start(self.time_label, expand=False, padding=8)

        randomBtn = gtk.ToggleButton("Shuffle")
        randomBtn.set_active(self.random)
        randomBtn.connect("toggled", self.toggle_random);
        views.pack_end(randomBtn, fill=True, expand=False, padding=8)

        # The content area where the song title and info will be shown:
        self.content_area = gtk.Label()
        self.content_area.set_use_markup(True)
        self.content_area.set_line_wrap(True)
        self.content_area.set_justify(gtk.JUSTIFY_CENTER)
        mainbox.pack_start(self.content_area, expand=False)

        # Add events we need to listen to:
        self.connect("key-press-event", self.key_press_event)

        self.add_events(gtk.gdk.SCROLL_MASK)
        self.connect("scroll-event", self.scroll_event)

        # Try to set a maximum size:
        self.set_size_request(550, 225)

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
                            self.songs.append(os.path.join(s, root, filename))
            elif s.endswith('.m3u'):
                if os.path.exists(s):
                    self.add_songs_in_playlist(s)
                elif os.path.exists(os.path.join(self.configdir, s)):
                    self.add_songs_in_playlist(os.path.join(self.configdir, s))
                else:
                    print s, ": No such playlist"
            else:
                if os.path.exists(s):
                    self.songs.append(s)
                else:
                    print s, ": No such file"

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
            print "No songs to play!"
            return

        self.connect("delete_event", self.quit)
        self.connect("destroy", self.quit)
        # self.winsig = self.connect("configure_event", self.configure_event)

        self.show_all()

        # set a timeout
        gobject.timeout_add(500, self.timer_func)

        gtk.main()

    def quit(self, w=None, data=None):
        self.save_playlist()
        gtk.main_quit()

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
        if self.play_state == MusicWin.PLAYING \
           or self.play_state == MusicWin.PAUSED:
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
            print "Current song doesn't seem to be in the list any more!"
            print cursong
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
        pos += self.skip_sec
        if pos < 0: pos = 0.
        self.skipped_seconds = pos
        mixer.music.play(0, pos)

    def skip_fwd(self, w=None):
        self.skip(10000)

    def skip_back(self, w=None):
        self.skip(-10000)

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
        dialog = gtk.MessageDialog(self,
                                   gtk.DIALOG_DESTROY_WITH_PARENT,
                                   gtk.MESSAGE_QUESTION,
                                   gtk.BUTTONS_OK_CANCEL,
                                   delstr)
        dialog.set_default_response(gtk.RESPONSE_OK)
        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_OK:
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
        '''Save the current playlist.'''
        if not self.playlist:
            print "No playlist to save to!"
            return

        if not os.path.exists(self.configdir):
            os.makedirs(configdir)

        if os.path.exists(self.playlist):
            os.rename(self.playlist, self.playlist + '.bak')

        fp = open(self.playlist, "w")
        newlist = self.songs[:]
        newlist.sort(reverse=self.backward)
        for song in newlist:
            fp.write(song + '\n')
        fp.close()

    def update_content_area(self):
        text = self.songs[self.song_ptr]
        has_title = False
        has_artist = False

        id3info = ID3.ID3(self.songs[self.song_ptr])
        # for k, v in id3info.items():
        #     if k == "ARTIST":
        #         has_artist = True
        #     elif k == "TITLE":
        #         has_title = True
        #     text += '\n' + k + ' : ' + v

        text += '<span size="25000">\n'
        try:
            text += cgi.escape(id3info['TITLE'])
        except KeyError:
            text += cgi.escape(os.path.basename(self.songs[self.song_ptr]))
        text += '\n'
        try:
            text += cgi.escape(id3info['ARTIST'])
        except KeyError:
            pass
        text += '</span>'

        self.content_area.set_label(unicode(text, 'utf-8', errors='replace'))

    def key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.q and \
           event.state == gtk.gdk.CONTROL_MASK:
            self.quit()
        elif event.keyval == gtk.keysyms.Left:
            self.prev_song()
        elif event.keyval == gtk.keysyms.Right:
            self.next_song()
        elif event.keyval == gtk.keysyms.Up:
            self.volume_up()
        elif event.keyval == gtk.keysyms.Down:
            self.volume_down()
        elif event.keyval == gtk.keysyms.space:
            self.pause()
        elif event.string == '.':
            self.stop()
        elif event.string == '0':
            self.restart()

        # d means delete from the current playlist;
        # ctrl-d actually deletes the song from disk.
        elif event.keyval == gtk.keysyms.d:
            if event.state == gtk.gdk.CONTROL_MASK:
                self.delete_song_from_disk()
            else:
                self.delete_song_from_playlist()

        elif event.keyval == gtk.keysyms.s and \
           event.state == gtk.gdk.CONTROL_MASK:
            print "Saving playlist"
            self.save_playlist()

        return True

    def scroll_event(self, widget, event):
        if event.direction == gtk.gdk.SCROLL_UP:
            self.volume_up()
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            self.volume_down()

    def sec_to_str(self, sec):
        '''Convert seconds (int) to h:m:s (string)'''
        s = sec % 60
        m = int(sec / 60)
        h = int(sec / 3600)
        if h:
            return '%d:%02d:%02d' % (h, m, s)
        else:
            return '%d:%02d' % (m, s)

    def timer_func(self):
        '''The timer func is what does the actual playing of songs.'''
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
        self.update_content_area()

        # Get the length:
        mp3info = MP3(self.songs[self.song_ptr])
        self.cur_song_length = mp3info.info.length
        self.cur_song_length_str = self.sec_to_str(self.cur_song_length)

        try:
            # Then load and play the song.
            mixer.music.load(self.songs[self.song_ptr])
            mixer.music.play()

            # Make sure the buttons are sane:
            self.pause_btn.set_label('||')
            self.stop_btn.set_label(u"\u25A0") # black square
        except Exception, e:
            print "Can't play", self.songs[self.song_ptr], ':', str(e)
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
            if args[0] == '-r' or args[0] == '--random':
                rand = True
                args = args[1:]
            elif args[0] == '-s' or args[0] == '--sequential':
                rand = False
                args = args[1:]
            elif args[0] == '-b' or args[0] == '--backward':
                backward = True
                rand = False
                args = args[1:]

        win = MusicWin(args, random=rand, backward=backward)
        win.run()
    else:
        sys.exit(0)

