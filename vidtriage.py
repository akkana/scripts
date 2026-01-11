#!/usr/bin/env python3

# A video player that also allows triaging videos while watching them,
# labeling them with numeric tags.
# Copyright 2023 by Akkana Peck -- share and enjoy under the GPLv2 or later.

# Basic video playing code came from https://stackoverflow.com/a/75268088

from tkinter import (
    Tk, Frame, Label, Button, Toplevel, StringVar,
    X, BOTH, Entry, DISABLED, END, HORIZONTAL, VERTICAL
)
from tkinter.ttk import Progressbar

from vlc import Instance, State

import time
import sys, os


class VLCwin:
    PROGRESSLENGTH = 600    # Length of the progressbar in pixels
    UPDATE_TIME = 100

    def __init__(self, vidlist):
        self.vidlist = vidlist
        self.vidlist_index = 0

        self.tags = {}

        # -q is supposed to turn off all the irritating chatter in the console,
        # but it doesn't. --no-xlib does suppress the output, weirdly.
        self.Instance = Instance('--no-xlib -q')
        self.player = self.Instance.media_player_new()
        self.fullscreen = 0
        self.root = Tk()
        self.root.title("vidtriage")

        # get the default background to use it when in non-fullscreen
        self.defaultbg = self.root.cget('bg')

        # self.root.geometry("900x750")

        self.frame = Frame(self.root, width=1200, height=700)
        self.frame.pack()

        # Set key bindings
        self.root.bind('<space>', self.spacebar)
        self.root.bind('<Escape>', self.toggle_fullscreen)

        self.root.bind('<Right>', self.skip_forward)
        self.root.bind('<Left>', self.skip_backward)

        self.root.bind('d', self.mark_for_deletion)
        self.root.bind('<Delete>', self.mark_for_deletion)
        self.root.bind('u', self.unmark_for_deletion)

        self.root.bind('q', self.quit)

        for c in range(0, 9):
            self.root.bind(chr(ord('0') + c), self.digit)

        # self.root.bind('<Expose>', self.expose)

        self.button_frame = Frame(self.root)
        self.button_frame.pack(expand=True, fill=X)

        self.vidlabeltext = StringVar()
        self.vidlabel = Label(self.button_frame,
                              textvariable=self.vidlabeltext)
        self.vidlabel.pack(side='left', expand=False)
        # self.vidlabel.grid(row=0, column=0)

        self.flagslabeltext = StringVar()
        self.flagslabel = Label(self.button_frame, bg='#eeffcc',
                                textvariable=self.flagslabeltext)
        self.flagslabel.pack(side='left', expand=False, padx=100)
        # self.flagslabel.grid(row=0, column=1)

        self.progress = Progressbar(self.button_frame,
                                    orient='horizontal',
                                    mode='determinate',
                                    length=__class__.PROGRESSLENGTH)
        self.progress.pack(side='left', expand=False)
        self.progress['value'] = 0

        self.fullscreen_btn = Button(
            self.button_frame, text="Full Screen (<ESC>)",
            command=self.toggle_fullscreen)
        self.fullscreen_btn.pack(side='right', expand=False)
        # self.fullscreen_btn.grid(row=0, column=2, sticky="E")

        # Set up a place to put the video when not in fullscreen mode
        self.display = Frame(self.frame, bd=4)
        self.display.place(relwidth=1, relheight=1)

        self.root.after(__class__.UPDATE_TIME, self.update_progress)

    def repack_buttons(self):
        self.button_frame.pack(expand=True, fill=X)
        self.vidlabel.pack(side='left', expand=False)
        self.flagslabel.pack(side='left', expand=True)
        self.fullscreen_btn.pack(side='right', expand=False)

    def start(self):
        # Calling play before mainloop, or on expose, makes VLC
        # play its videos in a new window.
        # Need to wait for the window to be drawn before calling play
        # to make sure the self.display is ready for it.
        self.root.after(400,
                        lambda: self.play(self.vidlist[self.vidlist_index]))

        self.root.mainloop()

    def play(self, vidsource=None):
        if not vidsource:
            vidsource = self.vidlist[self.vidlist_index]
        # print("Playing", vidsource)
        self.root.title("vidtriage: " + vidsource)

        Media = self.Instance.media_new(vidsource)
        self.player.set_xwindow(self.display.winfo_id())
        #setting the xwindow is for embedding the video
        self.player.set_media(Media)
        self.player.play()
        time.sleep(.1)
        self.duration = self.player.get_length()
        # print("duration: %.1f sec" % (self.duration/1000.))
        self.vidlabeltext.set("%s  %.1f sec" % (
            os.path.basename(self.vidlist[self.vidlist_index]),
            self.duration/1000.))
        self.flagslabeltext.set(self.get_vid_flags())

    def update_progress(self):
        if self.player.get_state() == State.Playing:
            self.progress['value'] = 100 * self.player.get_position()
        elif self.player.get_state() == State.Ended:
            if self.vidlist_index >= len(self.vidlist)-1:
                # Already on last video, wait for input
                return
            self.skip_forward()
            self.progress['value'] = 0

        self.root.after(__class__.UPDATE_TIME, self.update_progress)

    def get_vid_flags(self):
        flags = []
        for k in sorted(self.tags.keys()):
            if self.vidlist[self.vidlist_index] in self.tags[k]:
                if k == 'd':
                    flags.append("DELETE")
                else:
                    flags.append(k)
        return "Flags: " + ' '.join(flags)

    def toggle_fullscreen(self, event=False):
        # event can be True or False, or it could be an event
        if event is True:
            go_fullscreen = True
        elif event is False:
            go_fullscreen = False
        # elif self.fullscreen_btn.config('relief')[-1] == 'sunken':
        elif not self.fullscreen:
            go_fullscreen = True
        else:
            go_fullscreen = False

        if go_fullscreen:
            self.fullscreen = 1
            self.fullscreen_btn.config(relief="sunken")

            # pack forget removes the buttons from view
            self.button_frame.pack_forget()
            self.display.config(background="black")
            self.frame.pack_forget()
            self.frame.place(relwidth=1, relheight=1)

            # to make the frame fulscreen it must be unpacked and then placed
            self.root.attributes("-fullscreen", True)
        else:
            self.fullscreen_btn.config(relief="raised")
            self.frame.place_forget()
            self.frame.pack()
            self.repack_buttons()
            self.fullscreen = 0
            self.display.config(background=self.defaultbg)
            self.root.attributes("-fullscreen", False)

    def spacebar(self, event):
        """If in the middle of a video, toggle pause.
           If at the end, move to the next video.
        """
        if self.player.get_state() == State.Ended:
            self.vidlist_index += 1
            if self.vidlist_index >= len(self.vidlist):
                print("That was the last video")
                return

            self.player.set_pause(False)
            self.play(self.vidlist[self.vidlist_index])
            return

        pause = self.player.is_playing()
        self.player.set_pause(pause)
        # if pause:
        #     print("Paused at", self.player.get_position())

    def skip_forward(self, event=None):
        """Skip to the next video"""
        if self.vidlist_index >= len(self.vidlist)-1:
            print("Already on last video")
            return
        self.vidlist_index += 1
        # print("Skipping forward to", self.vidlist[self.vidlist_index])
        self.play(self.vidlist[self.vidlist_index])

    def skip_backward(self, event=None):
        """Skip to the previous video"""
        if self.vidlist_index == 0:
            print("Already on first video")
            return
        self.vidlist_index -= 1
        self.play(self.vidlist[self.vidlist_index])

    def digit(self, event):
        """Handle typed digits or 'd' """
        curvid = self.vidlist[self.vidlist_index]
        char = event.char
        if char not in self.tags:
            self.tags[char] = [ curvid ]
        elif curvid in self.tags[event.char]:
            self.tags[event.char].remove(curvid)
        else:
            self.tags[event.char].append(curvid)

        # print("Getting vid flags:", self.get_vid_flags())
        self.flagslabeltext.set(self.get_vid_flags())

    def mark_for_deletion(self, event):
        curvid = self.vidlist[self.vidlist_index]
        if "d" not in self.tags:
            self.tags["d"] = [curvid]
        elif curvid not in self.tags["d"]:
            self.tags["d"].append(curvid)
        self.skip_forward()

    def unmark_for_deletion(self, event):
        curvid = self.vidlist[self.vidlist_index]
        if "d" in self.tags and curvid in self.tags["d"]:
            self.tags["d"].remove(curvid)

    def quit(self, event):
        print("Tags:")
        for k in sorted(self.tags.keys()):
            if k == 'd':
                continue
            if not self.tags[k]:
                continue
            print(f"{ k }: { ' '.join(self.tags[k]) }")
        if 'd' in self.tags:
            print("\nDELETE:", ' '.join(self.tags['d']))
        sys.exit(0)


def main():
    win = VLCwin(sys.argv[1:])
    win.start()


if __name__ == '__main__':
    main()
