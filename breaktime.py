#!/usr/bin/env python3

# Reminder to get up and walk around if you've been at the computer
# for more than half an hour.

# Requires idle.py from gajim:
# https://dev.gajim.org/gajim/gajim/-/blob/89c7eb6e6ab3f61a188c6cee063a000526df522c/gajim/common/idle.py
# 

import idle

import time
import tkinter
# import signal
import sys, os


# Times are all in seconds

# How often should you get up and take time away from the computer?
GETUP_INTERVAL = 60 * 30

# How long, at minimum, do you have to stay away for it to count?
AWAY_MINIMUM = 60 * 4

# How often does the program wake up and poll?
POLL_INTERVAL = 30

# How much padding in the dialog, to make it a little bigger and more obvious
DIALOG_PADDING = 30

COLORS_NEEDBREAK = ("white", "darkred")
COLORS_NORMAL = ("black", "lightgrey")
COLORS_LONGENOUGH = ("black", "lightsteelblue")

DEBUG = False

# Timers counting idle and nonidle time
idle_start = 0
nonidle_start = 0

# The dialog button where messages will show
tkroot = None
button = None

WINWIDTH = 600
WINHEIGHT = 240


def create_window():
    global tkroot, button

    tkroot = tkinter.Tk(className="breaktime")
    # tkroot.overrideredirect(1)
    tkroot.title("Break Time")
    tkroot.withdraw()
    tkroot.resizable(False, False)

    def close():
        tkroot.withdraw()

    # Allocate enough space for three lines of text in the button:
    button = tkinter.Button(tkroot, text="""MMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMM""",
                            fg=COLORS_NORMAL[0],
                            activeforeground=COLORS_NORMAL[0],
                            bg=COLORS_NORMAL[1],
                            activebackground=COLORS_NORMAL[1],
                            font=("Serif", 18, "bold"),
                            # width=WINWIDTH, height=WINHEIGHT,
                            command=close)

    # make it a bit bigger than necessary
    button.pack(ipadx=DIALOG_PADDING, ipady=DIALOG_PADDING)

    # # Callback for key events:
    # def key_event(event):
    #     if event.char == 'q':
    #         sys.exit(0)
    # # Apparently we can't bind key events to a button, only to the dialog:
    # tkroot.bind("<Key>", key_event)

    # catch ctrl-C -- KeyboardInterrupt doesn't work from Tk
    # def handler(event):
    #     tkroot.destroy()
    # tkroot.bind_all('<Control-c>', handler)

    tkroot.resizable(False, False)

    tkroot.after(1, check)

    tkroot.mainloop()


def update_dialog(msg, colors=None, popup=True):
    if DEBUG:
        print("update_dialog:", msg)

    if colors:
        button["fg"] = colors[0]
        button["activeforeground"] = colors[0]
        button["bg"] = colors[1]
        button["activebackground"] = colors[1]

    button["text"] = msg   # Can also use button.config(text=message)
    if popup:
        tkroot.deiconify()
    return


# Return control to the shell before starting the loop:
# (disabled for testing)
# rc = os.fork()
# if rc:
#     sys.exit(0)


def check():
    global idle_start, nonidle_start

    now = time.time()
    idlesecs = idle.getIdleSec()
    # if DEBUG:
    #     print(f"\nnow: {int(now)}, idle for {int(idlesecs)}")
    if idlesecs < POLL_INTERVAL:
        # Currently nonidle
        idle_start = 0

        if not nonidle_start:
            # Going from idle to nonidle
            nonidle_start = now
            if idle_start and DEBUG:
                print("Starting nonidle timer after %.1f minutes idle"
                      % ((now - idle_start)/60))
        else:
            nonidle_time = now - nonidle_start
            msg = f"""You've been at the computer
for {(nonidle_time/60):.1f} min"""

            if nonidle_time > GETUP_INTERVAL:
                msg += "\nTime to take a break"
                update_dialog(msg=msg, colors=COLORS_NEEDBREAK)
            else:
                msg += f"\n(of {int(GETUP_INTERVAL/60)})"
                update_dialog(msg=msg, colors=COLORS_NORMAL, popup=False)
    else:
        # Currently idle
        idle_time = now - idle_start
        # if DEBUG:
        #     print(f"Idle time: {(idle_time/60):.1f} minutes")

        if not idle_start:
            idle_start = now
            if DEBUG:
                print("Starting away timer")
        elif idle_time >= AWAY_MINIMUM:
            # Away long enough
            # zero the nonidle timer so it can be restarted when nonidle
            if nonidle_start:
                nonidle_start = 0
            if button:
                msg = f"Away long enough,\n{(idle_time/60):.1f} minutes"
                update_dialog(msg=msg, colors=COLORS_LONGENOUGH, popup=False)
        else:
            update_dialog(msg=f"\nIdle for {(idle_time/60):.1f} minutes\n",
                          popup=False, colors=COLORS_NORMAL)

    tkroot.after(POLL_INTERVAL*1000, check)


def Usage():
    print("Usage: %s [-d] [max_time_at_computer [min_time_of_breaks]]"
          % (os.path.basename(sys.argv[0])))
    print("Times are in minutes. Defaults:")
    print("  Max %d (%.1f min) at computer"
          % (GETUP_INTERVAL, GETUP_INTERVAL/60))
    print("  Min %d (%.1f min) away" % (AWAY_MINIMUM, AWAY_MINIMUM/60))
    print("  -d: print debug messages")
    sys.exit(0)


if __name__ == '__main__':
    # Debug mode?
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        DEBUG = True
        sys.argv = sys.argv[1:]

    if not DEBUG:
        rc = os.fork()
        if rc:
            sys.exit(0)

    # Optional first argument, how often to interrupt, and second argument,
    # how long a break must be.
    try:
        GETUP_INTERVAL = int(sys.argv[1]) * 60
        if len(sys.argv) > 2:
            try:
                AWAY_MINIMUM = int(sys.argv[2]) * 60
            except ValueError:
                pass
            except:
                Usage()
    except IndexError:    # no argv[1]
        pass
    except:
        Usage()

    print("Max time at computer of %.1f min" % (GETUP_INTERVAL/60))
    print("Using min time away of %.1f min" % (AWAY_MINIMUM/60))
    try:
        create_window()

    except KeyboardInterrupt:
        if DEBUG:
            print("Keyboard Interrupt")
    # except:
    #     pass

    idle.close()

