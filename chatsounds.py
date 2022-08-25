#! /usr/bin/env python

# xchat script to play different sounds in different circumstances.
# Copyright 2012 by Akkana Peck, http://shallowsky.com.
# Share and enjoy under the GPLv2 or (at your option) any later version.

from __future__ import print_function

__module_name__ = "chatsounds"
__module_version__ = "0.3"
__module_description__ = "Plays sounds when it sees keywords"
__module_author__ = "Akkana Peck <akkana@shallowsky.com>"

import xchat
import sys, os, subprocess
import time

# Configuration: things you might want to change.
NORMAL_SOUND = "pop.wav"
SUBTLE_SOUND = "SingleClick.wav"
SPECIAL_SOUND = "akk.wav"
# Channels silenced by default, because they're too active:
SILENCED_CHANNELS = [ '#twitter_akkakk', '#python', '#linux', '##linux',
                      '#emacs', '#raspberrypi', '#ubuntu', '#xkcd' ]
# End configuration.

# The debugging log file.
# If it's set, we might get debug messages written to it.
Debug = None
# Debug = sys.stderr

def debugprint(*args, **kwargs):
    if 'file' not in kwargs:
        return
    outfile = kwargs['file']

    # Can't seem to pass just *args to print in python 2
    print(' '.join(map(str, args)), file=outfile)

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
            if self.current.poll() is None :
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
        if self.current and self.current.poll() is None :
            self.current.wait()

class XchatSoundHandler :
    """ Play alert sound depending on the channel and circumstances.
    """

    STARTUP_DELAY = 25     # No sounds will be played in the first few seconds

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

        self.sound_dir = os.path.expanduser("~/.config/hexchat/sounds/")

        self.silenced_channels = SILENCED_CHANNELS

        debugprint("Loaded chatsounds.py")

    def handle_message(self, word, word_eol, userdata):
        """
        Handle a message in xchat.
        word is something like:
          [ '\xaaaanick', "the message we're acting on" ]
          where aaaa is a number like \x0328
          This, incidentally, is not what the doc says it should be at
          http://xchat.org/docs/xchatpython.html
        userdata is something like: 'Channel Message', from EVENTS,
        so you can play different sounds depending on what happened.
        """

        if len(word) < 1:
            return

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

        # For debugging. But this goes to the channel and makes things
        # hard to follow. Would be better to debug to a log file.
        if Debug :
            debugprint("Channel %s, network %s: %s" % (str(channel), str(network),
                                                  str(line)), file=Debug)

        # Now, customize the rest as desired. Here are some examples:

        # Anyone addressing or mentioning my nick:
        if line.find(mynick) > 0 and word[0] != 'NickServ' :
            if Debug :
                debugprint(">>> chatsounds", userdata,
                      "network =", network,
                      "channel =", channel,
                      ">>>>> Contains my nick!", userdata,
                      line,
                      file=Debug)
            self.player.play(os.path.join(self.sound_dir, SPECIAL_SOUND))
            return xchat.EAT_NONE

        if userdata == "Channel Msg Hilight" or \
                userdata == "Channel Action Hilight" :
            #if channel == 'root' || channel == '&bitlbee'
            # Don't play sounds for bitlbee channel actions,
            # because it's constantly losing connection and restarting.
            # In fact, if we could just delete those tabs it would be great.
            if network != 'Bitlbee' :
                if Debug :
                    debugprint(">>> chatsounds", userdata,
                          "network =", network,
                          "channel =", channel,
                          file=Debug)
                self.player.play(os.path.join(self.sound_dir, SPECIAL_SOUND))
            else:
                if Debug :
                    debugprint(">>> chatsounds skipping bitlbee",
                          userdata, "network =", network,
                          "channel =", channel,
                          file=Debug)
            return xchat.EAT_NONE

        # Private message:
        elif userdata.startswith("Private Message") :
            if channel == "root":
                if Debug :
                    debugprint("Skipping channel==root")
            else:
                if Debug :
                    debugprint(">>> chatsounds private message!",
                          userdata,
                          "network =", network,
                          "channel =", channel,
                          file=Debug)
                self.player.play(os.path.join(self.sound_dir, SPECIAL_SOUND))
            return xchat.EAT_NONE

        # Now check whether we're silenced.
        # Note that nick references and private messages are exempt
        # from this check -- you'll hear them even on silenced channels.
        if channel in self.silenced_channels :
            return xchat.EAT_NONE

        # More subtle sound for bitlbee/twitter, since they're so numerous:
        if channel == "#twitter_" + mynick :
            # print ">>>>> Twitter channel!"
            self.player.play(os.path.join(self.sound_dir, SUBTLE_SOUND))

        # if you want to be fairly noisy or don't have many active channels,
        # you might want an alert for every channel message:
        elif userdata.startswith("Channel M") or \
                userdata.startswith("Channel Action") :
            self.player.play(os.path.join(self.sound_dir, NORMAL_SOUND))

        return xchat.EAT_NONE

    def handle_prefs(self, word, word_eol, userdata) :
        """ Use this for any prefs/actions, like silence/unsilence.
        """
        channel = xchat.get_info('channel')

        if word[1] == 'silence' :
            if channel not in self.silenced_channels :
                self.silenced_channels.append(channel)
            debugprint("chatsounds: silenced", channel, self.silenced_channels)
        elif word[1] == 'unsilence' :
            if channel in self.silenced_channels :
                self.silenced_channels.remove(channel)
            debugprint("chatsounds: unsilenced", channel, self.silenced_channels)

        return xchat.EAT_ALL

if __name__ == "__main__" :
    # Debug log, line buffered:
    Debug = open("/tmp/chatsounds.log", "w", buffering=1)

    chathandler = XchatSoundHandler()

