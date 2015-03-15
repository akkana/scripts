#! /usr/bin/env python

import sys, os
import time
import random

from pygame import mixer
import ID3

import gtk, gobject
import pango

class MusicWin(gtk.Window) :
    def __init__(self, init_songs):
        super(MusicWin, self).__init__()

        self.songs = []
        self.song_ptr = -1

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
        self.content_area = gtk.Label()
        self.content_area.set_use_markup(True)
        self.content_area.set_justify(gtk.JUSTIFY_CENTER)
        mainbox.add(self.content_area)

        views = gtk.HBox(spacing=4)
        mainbox.add(views)
        self.time_label = gtk.Label()
        views.add(self.time_label)

        buttonbox = gtk.HBox(spacing=4)
        mainbox.add(buttonbox)

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
            else:
                self.songs.append(s)

        # Play music in random order:
        random.seed(os.getpid())
        random.shuffle(self.songs)

    def run(self):
        self.connect("delete_event", gtk.main_quit)
        self.connect("destroy", gtk.main_quit)
        # self.winsig = self.connect("configure_event", self.configure_event)

        self.show_all()

        # set a timeout
        gobject.timeout_add(500, self.timer_func)

        gtk.main()

    def restart(self, w):
        #mixer.music.rewind()
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

        text += '<span size="25000">'
        try:
            text += '\n' + id3info['TITLE']
        except ID3.InvalidTagError:
            pass
        try:
            text += '\n' + id3info['ARTIST']
        except ID3.InvalidTagError:
            pass
        text += '</span>'

        self.content_area.set_label(text)

    def timer_func(self):
        # If we're stopped, don't change anything.
        if self.play_state == MusicWin.STOPPED:
            return True

        # Are we still playing the same song?
        if mixer.music.get_busy():
            # This sadly still isn't right. Sigh.
            self.time_label.set_label(str(int(self.skipped_seconds
                                              + mixer.music.get_pos()/1000)))
            return True

        # Else time to play the next song.
        self.skipped_seconds = 0
        self.song_ptr = (self.song_ptr + 1) % len(self.songs)
        self.update_content_area()
        mixer.music.load(self.songs[self.song_ptr])
        mixer.music.play()
        return True

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print "Usage:", sys.argv[0], "files or directories"
        sys.exit(1)

    rc = os.fork()
    if not rc:
        win = MusicWin(sys.argv[1:])
        win.run()
    else:
        sys.exit(0)

# Other things we can do once we have a UI:
# mixer.set_volume(.9)
# mixer.music.pause()


