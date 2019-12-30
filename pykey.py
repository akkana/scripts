#!/usr/bin/env python

"""
Simulate keypresses under X. A simpler, Python version of Crikey,
http://shallowsky.com/software/crikey/
"""

# Copyright 2018 by Akkana Peck; share and enjoy under the GPLv2 or later.

import Xlib.display
import Xlib.X
import Xlib.XK
import Xlib.protocol.event

UseXTest = True

try:
    import Xlib.ext.xtest
except ImportError:
    UseXTest = False
    print "no XTest extension; using XSendEvent"

import sys, time

display = None

def init_display():
    global display, UseXTest
    display = Xlib.display.Display()
    # window = display.get_input_focus()._data["focus"]

    if UseXTest and not display.query_extension("XTEST"):
        UseXTest = False

special_X_keysyms = {
    ' ': "space",
    '\t': "Tab",
    '\n': "Return",  # for some reason this needs to be cr, not lf
    '\r': "Return",
    '\e': "Escape",
    '!': "exclam",
    '#': "numbersign",
    '%': "percent",
    '$': "dollar",
    '&': "ampersand",
    '"': "quotedbl",
    '\'': "apostrophe",
    '(': "parenleft",
    ')': "parenright",
    '*': "asterisk",
    '=': "equal",
    '+': "plus",
    ',': "comma",
    '-': "minus",
    '.': "period",
    '/': "slash",
    ':': "colon",
    ';': "semicolon",
    '<': "less",
    '>': "greater",
    '?': "question",
    '@': "at",
    '[': "bracketleft",
    ']': "bracketright",
    '\\': "backslash",
    '^': "asciicircum",
    '_': "underscore",
    '`': "grave",
    '{': "braceleft",
    '|': "bar",
    '}': "braceright",
    '~': "asciitilde"
    }

# A few characters that aren't easy to map:
special_X_keycodes = {
    'b' : 22,
    'n' : 36,
    't' : 23
}

def get_keysym(ch):
    keysym = Xlib.XK.string_to_keysym(ch)
    if keysym == 0:
        # Unfortunately, although this works to get the correct keysym
        # i.e. keysym for '#' is returned as "numbersign"
        # the subsequent display.keysym_to_keycode("numbersign") is 0.
        keysym = Xlib.XK.string_to_keysym(special_X_keysyms[ch])
    return keysym

def is_shifted(ch):
    """Return False if the character isn't shifted.
       If it is, return the unshifted character.
    """
    if ch.isupper():
        return ch.lower()
    if "~!@#$%^&*()_+{}|:\"<>?".find(ch) >= 0:
        return ch    # XXX There's no way to easily map these
    return False

def char_to_keycode(ch):
    keysym = get_keysym(ch)
    keycode = display.keysym_to_keycode(keysym)
    if keycode == 0:
        print "Sorry, can't map", ch

    return keycode

# Bit masks for modifier keys
MOD_SHIFT = 1
MOD_CTRL = 2
MOD_ALT = 4
MOD_META = 8

# Get these from xev:
SHIFT_KEYCODE = 50
CTRL_KEYCODE = 37
ALT_KEYCODE = 64
META_KEYCODE = 133

def send_modifier(keycode, down):
    """This only applies with UseXTest.
       With Xlib.protocol.event, modifiers are flags on each key.
    """
    print "send_modifier", keycode, down
    if not UseXTest:
        return
    if down:
        Xlib.ext.xtest.fake_input(display, Xlib.X.KeyPress, keycode)
    else:
        Xlib.ext.xtest.fake_input(display, Xlib.X.KeyRelease, keycode)

def send_key(keycode, shift_down, ctrl_down, alt_down, meta_down):
    print "send_key", keycode, shift_down, ctrl_down, alt_down, meta_down
    if UseXTest:
        Xlib.ext.xtest.fake_input(display, Xlib.X.KeyPress, keycode)
        Xlib.ext.xtest.fake_input(display, Xlib.X.KeyRelease, keycode)

    else:
        mod_mask = 0
        if shift_down:
            mod_mask |= Xlib.X.ShiftMask
        if ctrl_down:
            mod_mask |= Xlib.X.ControlMask

        # I don't know which masks alt and meta/windows correspond to;
        # these are just guesses.
        if alt_down:
            mod_mask |= Xlib.X.Mod1Mask
        if meta_down:
            mod_mask |= Xlib.X.Mod2Mask

        window = display.get_input_focus()._data["focus"]
        event = Xlib.protocol.event.KeyPress(
            time = int(time.time()),
            root = display.screen().root,
            window = window,
            same_screen = 0, child = Xlib.X.NONE,
            root_x = 0, root_y = 0, event_x = 0, event_y = 0,
            state = mod_mask,
            detail = keycode
            )
        window.send_event(event, propagate = True)
        event = Xlib.protocol.event.KeyRelease(
            time = int(time.time()),
            root = display.screen().root,
            window = window,
            same_screen = 0, child = Xlib.X.NONE,
            root_x = 0, root_y = 0, event_x = 0, event_y = 0,
            state = mod_mask,
            detail = keycode
            )
        window.send_event(event, propagate = True)

def send_string(s):
    """Generate fake keypresses to send the given string,
       using XTest if possible, otherwise Xlib.
       \C means press ctrl, \c means release it; same for s (shift),
       a (alt) and m or w (meta/windows).
       All modifiers will be released at the end of a string if the
       release code isn't already in the specifier.
    """
    init_display()

    # Make lists of all the keycodes and whether they're shifted:
    keycodes = []
    modifiers = []
    shift_down = False
    ctrl_down = False
    alt_down = False
    meta_down = False
    backslash = False

    for ch in s:
        # print ("\n============ Considering '%s'" % ch)
        if ch == '\\':
            backslash = True
            continue

        if backslash:
            backslash = False

            # Most backslash escapes will be modifiers:
            if ch == 'C':
                ctrl_down = True
                send_modifier(CTRL_KEYCODE, True)
                continue
            elif ch == 'A':
                alt_down = True
                send_modifier(ALT_KEYCODE, True)
                continue
            elif ch == 'M' or ch == 'W':
                meta_down = True
                send_modifier(META_KEYCODE, True)
                continue
            elif ch == 'c':
                ctrl_down = False
                send_modifier(CTRL_KEYCODE, False)
                continue
            elif ch == 'a':
                alt_down = False
                send_modifier(ALT_KEYCODE, False)
                continue
            elif ch == 'm' or ch == 'w':
                meta_down = False
                send_modifier(META_KEYCODE, False)
                continue

            # but a few may be other characters:
            elif ch in special_X_keycodes:
                keycode = special_X_keycodes[ch]
                send_key(keycode, shift_down, ctrl_down, alt_down, meta_down)
                continue

            # Else just ignore the backslash and use the letter.

        ch_unshifted = is_shifted(ch)
        if ch_unshifted:
            if not shift_down:
                send_modifier(SHIFT_KEYCODE, True)
                shift_down = True
            ch = ch_unshifted
        else:
            if shift_down:
                send_modifier(SHIFT_KEYCODE, False)
                shift_down = False

        keycode = char_to_keycode(ch)
        send_key(keycode, shift_down, ctrl_down, alt_down, meta_down)

    # Is anything still pressed?
    if shift_down:
        send_modifier(SHIFT_KEYCODE, False)
    if ctrl_down:
        send_modifier(CTRL_KEYCODE, False)
    if alt_down:
        send_modifier(ALT_KEYCODE, False)
    if meta_down:
        send_modifier(META_KEYCODE, False)

    display.sync()

if __name__ == '__main__':
    for arg in range(1, len(sys.argv)):
        send_string(sys.argv[arg])
