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
GETUP_INTERVAL = 60 * 15    # 30

# How long, at minimum, do you have to stay away for it to count?
AWAY_MINIMUM = 60 * 4

# How often does the program wake up and poll?
POLL_INTERVAL = 30

# How much padding in the dialog, to make it a little bigger and more obvious
DIALOG_PADDING = 50

# Timers counting idle and nonidle time
idle_start = 0
nonidle_start = 0

# The dialog button where messages will show
tkroot = None
button = None


def create_window():
    global tkroot, button

    tkroot = tkinter.Tk()
    # tkroot.overrideredirect(1)
    tkroot.title("Break Time")
    tkroot.withdraw()
    tkroot.resizable(False, False)

    def close():
        global nonidle_start
        nonidle_start = 0
        tkroot.withdraw()

    button = tkinter.Button(tkroot, text="""MMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMM""",
                            bg="red", activebackground="red",
                            fg="white", activeforeground="white",
                            font=("Sans", 28, "bold"),
                            command=close)

    # make it a bit bigger than necessary
    button.pack(ipadx=DIALOG_PADDING, ipady=DIALOG_PADDING)

    # Callback for key events:
    def key_event(event):
        # print(event.char, event.keysym, event.keycode)
        if event.char == 'q':
            sys.exit(0)
    # Apparently we can't bind key events to a button, only to the dialog:
    tkroot.bind("<Key>", key_event)

    # catch ctrl-C -- KeyboardInterrupt doesn't work from Tk
    # def handler(event):
    #     tkroot.destroy()
    #     print('caught ^C')
    # tkroot.bind_all('<Control-c>', handler)

    tkroot.after(1, check)

    tkroot.mainloop()


def alert_getup(t):
    global button
    print("alert_getup", t)

    message = f"""You've been at the computer
for {int(t // 60)} minutes:
time to take a break"""
    print(message)
    button["text"] = message   # Can also use button.config(text=message)
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
    # print(f"\nnow: {int(now)}, idle for {int(idlesecs)}")
    if idlesecs < POLL_INTERVAL:
        # Currently nonidle
        idle_start = 0

        if not nonidle_start:
            # Going from idle to nonidle
            nonidle_start = now
            if idle_start:
                print("Starting nonidle timer after %.1f minutes idle"
                      % ((now - idle_start)/60))
        else:
            nonidle_time = now - nonidle_start
            if nonidle_time > GETUP_INTERVAL:
                alert_getup(nonidle_time)
            else:
                print(f"nonidle time {(nonidle_time / 60):.1f} minutes")
    else:
        # Currently idle
        idle_time = now - idle_start
        print("Idle time:", int(idle_time))
        if not idle_start:
            idle_start = now
            print("Starting away timer")
        elif idle_time >= AWAY_MINIMUM:
            # Away long enough
            # zero the nonidle timer so it can be restarted when nonidle
            if nonidle_start:
                nonidle_start = 0
            print(f"Away long enough, {(idle_time/60):.1f} minutes")
            if button:
                button["text"] = f"Away long enough,\n{(idle_time/60):.1f} minutes"
        elif button:
            # print("Still away, that's good")
            button["text"] = f"\nIdle for {(idle_time/60):.1f} minutes\n"

    # time.sleep(POLL_INTERVAL)
    tkroot.after(POLL_INTERVAL*1000, check)


if __name__ == '__main__':
    try:
        create_window()

    except KeyboardInterrupt:
        print("Keyboard Interrupt")
    # except:
    #     pass

    idle.close()

