#!/usr/bin/env python3

# Reminder to get up and walk around if you've been at the computer
# for more than half an hour.

# Requires idle.py from gajim:
# https://dev.gajim.org/gajim/gajim/-/blob/89c7eb6e6ab3f61a188c6cee063a000526df522c/gajim/common/idle.py
#

# ipcsimple comes from Akkana's scripts repository, same as this script
import ipcsimple

import idle

import time
import tkinter
import signal
import sys, os


# Times are all in seconds

# How often should you get up and take time away from the computer? (minutes)
GETUP_INTERVAL = 30

# How long, at minimum, do you have to stay away for it to count? (minutes)
AWAY_MINIMUM = 4

# How often does the program wake up and poll?
POLL_INTERVAL = 30

# How much padding in the dialog, to make it a little bigger and more obvious
DIALOG_PADDING = 30

COLORS_NEEDBREAK = ("white", "darkred")
COLORS_NORMAL = ("black", "lightgrey")
COLORS_LONGENOUGH = ("black", "palegreen")

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

    tkroot.after(1000, poll_for_time)

    ipcsimple.set_ipc_handler(communicate)
    tkroot.after(50, poll_for_signals)  #  time in ms.

    tkroot.mainloop()


def poll_for_time():
    msg, colors, font = get_check_msg()
    update_dialog(msg=msg, popup=("bold" in font), colors=colors, font=font)

    tkroot.after(POLL_INTERVAL*1000, poll_for_time)


def poll_for_signals():
    """This controls how promptly the Tk app can respond to a signal"""
    tkroot.after(1000, poll_for_signals)  #  time in ms.


def communicate(bytestring=None):
    """Called by the ipc_handler that is invoked on a SIGUSR1.
       Return a string that will be sent through the handler.
       bytestring is probably None and will be ignored.
    """
    return get_check_msg()


def update_dialog(msg, colors=None, popup=True, font=None):
    if DEBUG:
        print("update_dialog:", msg)

    if colors:
        button["fg"] = colors[0]
        button["activeforeground"] = colors[0]
        button["bg"] = colors[1]
        button["activebackground"] = colors[1]

    if font:
        button["font"] = font

    button["text"] = msg   # Can also use button.config(text=message)
    if popup:
        tkroot.deiconify()
    return


# Return control to the shell before starting the loop:
# (disabled for testing)
# rc = os.fork()
# if rc:
#     sys.exit(0)


def get_check_msg():
    """Figure out the current status/time left.
       Return message, color, font for the dialog
       (also used when querying from an external process).
    """
    global idle_start, nonidle_start

    msg = None
    colors = None
    font = None

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
                return msg, COLORS_NEEDBREAK, ("Serif", 18, "bold")
            else:
                msg += f"\n(of {int(GETUP_INTERVAL/60)})"
                return msg, COLORS_NORMAL, ("Serif", 18, "normal")

    # Else currently idle

    if not idle_start:
        idle_start = now
        if DEBUG:
            return "Starting away timer", COLORS_NORMAL, ("Serif", 18, "normal")

    idle_time = now - idle_start

    if idle_time >= AWAY_MINIMUM:
        # Away long enough
        # zero the nonidle timer so it can be restarted when nonidle
        if nonidle_start:
            nonidle_start = 0
        msg = f"Away long enough,\n{(idle_time/60):.1f} minutes"
        return msg, COLORS_LONGENOUGH, ("Serif", 18, "bold")

    # else still idle
    return ( f"\nIdle for {(idle_time/60):.1f} minutes\n",
             COLORS_NORMAL, ("Serif", 18, "normal") )


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=\
        """Monitor time spent at the computer, and suggest taking breaks.
Times should be specified in minutes.""")
    parser.add_argument('-d', "--debug", dest="debug", default=False,
                        action="store_true", help="Print debugging messages")
    parser.add_argument('-q', "--query", dest="query", default=False,
                        action="store_true",
                        help="Query running instance for current status")
    parser.add_argument('-b', '--break', dest='min_break_time',
                        default=AWAY_MINIMUM, nargs='?', type=float,
                        help='Minimum time for a break')
    parser.add_argument('max_time', nargs='?', type=float,
                        default=GETUP_INTERVAL,
                      help='Maximum time at the computer before taking a break')
    args = parser.parse_args(sys.argv[1:])

    # Debug mode?
    if args.debug:
        DEBUG = True

    if args.query:
        try:
            pidlist = ipcsimple.list_procs("breaktime", uid=os.getuid())
            for pid in pidlist:
                pid = int(pid)
                result = ipcsimple.ping_running_process(pid)
                print("Process", pid, "status:")
                print(result)
        except RuntimeError as e:
            print("Couldn't find a running breaktime:", e)

        sys.exit(0)

    # Should only allow one running instance of breaktime
    ipcsimple.kill_instances("breaktime")

    if not DEBUG:
        rc = os.fork()
        if rc:
            sys.exit(0)

    GETUP_INTERVAL = args.max_time * 60
    AWAY_MINIMUM = args.min_break_time * 60

    print("Max time at computer of %.1f min" % (GETUP_INTERVAL/60))
    print("Min time away of %.1f min" % (AWAY_MINIMUM/60))

    try:
        create_window()

    except KeyboardInterrupt:
        if DEBUG:
            print("Keyboard Interrupt")
    # except:
    #     pass

    idle.close()

