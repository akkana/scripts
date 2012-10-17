#! /usr/bin/env python

# xchat script to play different sounds in different circumstances.
# Copyright 2012 by Akkana Peck, http://shallowsky.com.
# Share and enjoy under the GPLv2 or (at your option) any later version.

__module_name__ = "chatsounds" 
__module_version__ = "0.1" 
__module_description__ = "Plays sounds when it sees keywords"
__module_author__ = "Akkana Peck <akkana@shallowsky.com>"

import xchat
import sys, os, subprocess
import time

class SoundPlayer :
    """
       Play sounds that don't overlap in time.
    """

    PLAYER = "/usr/bin/aplay"

    def __init__(self) :
        self.curpath = None
        self.current = None

    def __del__(self) :
        self.wait()

    def play(self, path) :
        if self.current :
            if self.current.poll() == None :
                # Current process hasn't finished yet. Is this the same sound?
                if path == self.curpath :
                    # A repeat of the currently playing sound.
                    # Don't play it more than once.
                    #print path, "is still playing. Not playing again"
                    return
                else :
                    # Trying to play a different sound.
                    # Wait on the current sound then play the new one.
                    #print "Different sound; first waiting for", self.curpath
                    self.wait()
            self.current = None
            self.curpath = None

        #print "Trying to play", path

        self.curpath = path
        self.current = subprocess.Popen([ SoundPlayer.PLAYER, '-q', path ] )

    def wait(self) :
        if self.current and self.current.poll() == None :
            self.current.wait()

class XchatSoundHandler :
    ''' Play alert sound depending on the channel and circumstances.
    '''

    STARTUP_DELAY = 15     # No sounds will be played in the first few seconds

    # Xchat events. Comment out any events for which you don't want alerts:
    EVENTS = [
        "Channel Action",
        "Channel Action Hilight",
        "Channel Message",
        "Channel Msg Hilight",
        "Channel Notice",
        "Generic Message",
        "Kick",
        "Killed",
        #  "Motd",
        "Notice",
        #  "Part with Reason",
        "Private Message",
        "Private Message to Dialog",
        #  "Quit",
        "Receive Wallops",
        "Server Notice",
        "Server Text",
        #  "Topic",
        #  "Topic Change",
        ]

    def __init__(self) :
        self.start_time = time.time()
        for event in XchatSoundHandler.EVENTS :
            xchat.hook_print(event, self.handle_message, event)

        xchat.hook_command("chatsounds", self.handle_prefs)
        xchat.hook_command("cs", self.handle_prefs)

        self.player = SoundPlayer()

        self.sound_dir = os.path.expanduser("~/.xchat2/sounds/")

        self.silenced_channels = []

        print "Loaded chatsounds.py"

    def handle_message(self, word, word_eol, userdata):
        '''
        Handle a message in xchat.
        word is something like:
          [ '\xaaaanick', "the message we're acting on" ]
          where aaaa is a number like \x0328
          This, incidentally, is not what the doc says it should be at
          http://xchat.org/docs/xchatpython.html
        userdata is something like: 'Channel Message', from EVENTS,
        so you can play different sounds depending on what happened.
        '''

        # If it's too soon after startup, don't do anything.
        # Then we won't hear a slew of alerts from past scrollback,
        # NickServ 'You are now identified for" messages, etc.
        if time.time() - self.start_time < XchatSoundHandler.STARTUP_DELAY :
            return xchat.EAT_NONE

        # You may want to use channel name, network name or variables
        # in the xchat context to decide which alerts to play.
        channel = xchat.get_info('channel')
        network = xchat.get_info('network')
        ctxt = xchat.get_context()
        mynick = ctxt.get_info("nick")
        line = word[1]

        # Are we silenced?
        if channel in self.silenced_channels :
            return xchat.EAT_NONE

        # Now, customize the rest as desired. Here are some examples:

        # Anyone addressing or mentioning my nick:
        if line.find(mynick) > 0 and word[0] != 'NickServ' or \
               userdata == "Channel Msg Hilight" or \
               userdata == "Channel Action Hilight" :
            # print ">>>>> Contains my nick!", userdata, ">>", line
            self.player.play(os.path.join(self.sound_dir, "akk.wav"))

        # Private message:
        elif userdata.startswith("Private Message") :
            # print ">>>>> Private message!"
            self.player.play(os.path.join(self.sound_dir, "akk.wav"))

        # More subtle sound for bitlbee/twitter, since they're so numerous:
        elif channel == "#twitter_" + mynick :
            # print ">>>>> Twitter channel!"
            self.player.play(os.path.join(self.sound_dir, "SingleClick.wav"))

        # if you want to be fairly noisy or don't have many active channels,
        # you might want an alert for every channel message:
        elif userdata.startswith("Channel M") or \
                userdata.startswith("Channel Action") :
            self.player.play(os.path.join(self.sound_dir, "pop.wav"))

        return xchat.EAT_NONE

    def handle_prefs(self, word, word_eol, userdata) :
        ''' Use this for any prefs/actions, like silence/unsilence.
        '''
        channel = xchat.get_info('channel')

        if word[1] == 'silence' :
            if channel not in self.silenced_channels :
                self.silenced_channels.append(channel)
            print "chatsounds: silenced", channel, self.silenced_channels
        elif word[1] == 'unsilence' :
            if channel in self.silenced_channels :
                self.silenced_channels.remove(channel)
            print "chatsounds: unsilenced", channel, self.silenced_channels

        return xchat.EAT_ALL

if __name__ == "__main__" :
    chathandler = XchatSoundHandler()

