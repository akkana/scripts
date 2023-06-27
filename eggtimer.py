#!/usr/bin/env python

from __future__ import print_function

import sys, os
import time
import signal
import socket

wakeuptime = None
message = "Wake up!"


SLASHPROC = "/proc"


# Tkinter changed capitalization from Python 2 to Python 3.
# Python 2: import Tkinter as tkinter
# Python 3: import tkinter
# The error trying to import a nonexistent module also changed:
# Python2 raises ImportError, while Python3 raises ModuleNotFoundError
# which is a class of ImportError. Use ImportError because both
# Python versions understand it.
try:
    import tkinter
    # This may throw ImportError in Python 2 or ModuleNotFoundError in Py 3.
except ImportError:
    # In case it's Python 2, try importing it the Python 2 way:
    try:
        import Tkinter as tkinter
    except ImportError:
        print("Sorry, ImportError, eggtimer needs Tkinter")
        sys.exit(1)


# Callback for key events:
def keyEvent(event):
    # print(event.char, event.keysym, event.keycode)
    if event.char == 'q' or event.keysym == 'Return':
        sys.exit(0)


def showAlert(message:str):
    # Try to beep a bit, even though that doesn't work on some distros:
    print("")

    root = tkinter.Tk()

    button = tkinter.Button(root, text=message,
                            bg="red", activebackground="red",
                            fg="white", activeforeground="white",
                            font=("Sans", 40, "bold"),
                            command=quit)

    # Make sure the window is at least as big as the screen:
    button.pack(ipadx=root.winfo_screenwidth()/2,
                ipady=root.winfo_screenheight()/2)

    # Apparently we can't bind key events to a button, only to the root:
    root.bind("<Key>", keyEvent)

    root.mainloop()


def is_eggtimer_proc(pid):
    try:
        # Look for other eggtimer processes
        with open(os.path.join(SLASHPROC, str(pid), "cmdline")) as fp:
            cmdline = fp.read().split('\0')
            if "python" not in cmdline[0]:
                return False
            if not (cmdline[1].endswith("eggtimer") or
                    cmdline[1].endswith("eggtimer.py")):
                return False
            return True
    except:
        # Likely a non/integer directory or file in /proc
        return False


def get_eggtimer_procs():
    """Find all running eggtimer processes. Return list of int pids."""

    pidlist = []
    for pid in os.listdir(SLASHPROC):
        # Skip the current process' PID
        try:
            pidint = int(pid)
        except:
            continue
        if pidint == os.getpid():
            continue

        if is_eggtimer_proc(pid):
            pidlist.append(pidint)

    return pidlist


def user_timestr(secs):
    if secs > 60*60*24:
        return time.strftime("%-d days %-H hours %-M minutes %-S seconds",
                             time.gmtime(secs))
    if secs > 60*60:
        return time.strftime("%-H hours %-M minutes %-S seconds",
                             time.gmtime(secs))
    if secs > 60:
        return time.strftime("%-M minutes %-S seconds",
                             time.gmtime(secs))
    return time.strftime("%-S seconds",
                         time.gmtime(secs))


# Set up a signal handler so users can query for time left
def handle_wakeup(signal, frame):
    global wakeuptime

    timeleft = int(wakeuptime - time.time())
    # print(f"In {user_timestr(timeleft)}: {message}")

    # Set up a socket for full-duplex communication:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sockname = f"/tmp/eggtimer.{os.getpid()}"
    if not os.path.exists(sockname):
        sock.bind(sockname)
        sock.listen(1)
        conn, addr = sock.accept()

        while True:
            data = conn.recv(1024)
            if not data:
                break

            endtime = time.strftime('%H:%M',
                                    time.localtime(time.time() + timeleft))

            if data == b"STATUS":
                print("checking status")
                conn.sendall(f"In {user_timestr(timeleft)} (at {endtime}): "
                             f"{message} (PID {os.getpid()})".encode())

            elif data.startswith(b"ADD "):
                try:
                    addsecs = float(data[4:]) * 60
                    timeleft += addsecs
                    wakeuptime += addsecs

                    conn.sendall(f"Adding {addsecs} seconds, "
                                 f"now {user_timestr(timeleft)}"
                                 f"({endtime})".encode())
                except ValueError:
                    conn.sendall(f"Can't add {data[4:]} seconds".encode())

            else:
                conn.sendall(b"Unknown command: " + data)

        conn.close()
        os.unlink(sockname)

    else:
        print("Socket already existed")

    # Go back to sleep, perhaps with an updated sleep time
    time.sleep(timeleft)

    showAlert(message)


def ping_running_eggtimers(cmd_tuples):
    """Ping running eggtimer processes, send commands to them if any are
       supplied, then report status for each of them.

       cmd_tuples (optional) is a list of [ (pid, command [, arg] ) ]
       e.g. [ (7563, ADD, 60), (8725, SUBTRACT, 45), (9203, -3 ]
       If there's no explicit command, ADD is assumed (but the
       value can be negative).

       If cmd_tuples are supplied, ping all the referenced PIDs,
       else ping all running eggtimers asking for status.
    """
    if not cmd_tuples:
        timer_pids = get_eggtimer_procs()
        if not timer_pids:
            print("Couldn't find any eggtimers still running", file=sys.stderr)
            sys.exit(1)
        cmd_tuples = [ (pid,) for pid in timer_pids ]

    for ctup in cmd_tuples:
        pidint = int(ctup[0])

        # Make sure it's actually an eggtimer process -- don't
        # be sending signals to other processes.
        if not is_eggtimer_proc(pidint):
            print(pidint, "isn't an eggtimer process!", file=sys.stderr)
            continue

        # Wake up the process and tell it to create a socket
        os.kill(pidint, signal.SIGUSR1)

        # Look for Unix-domain socket named /tmp/eggtimer.[pid]
        # May have to wait a little while for it to be created,
        # but don't wait forever.
        sockname = f"/tmp/eggtimer.{pidint}"
        for i in range(10):
            if os.path.exists(sockname):
                break
            time.sleep(.15)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(sockname)

        multiplier = 0
        for cmd in ctup[1:]:
            # A number, like +2 or -3, means adding minutes
            # (which can be negative).
            if cmd == 'ADD':
                multiplier = 1
                continue    # ADD is implied

            if cmd == 'SUBTRACT' or cmd == 'SUB':
                multiplier = -1
                continue

            if cmd[0] in '-+' or multiplier:
                try:
                    add_time = float(cmd)
                except ValueError:
                    print("Can't add", cmd, ": not a time", file=sys.stderr)
                    continue
                if multiplier:
                    add_time *= multiplier
                sock.sendall(f"ADD {add_time}".encode())
                response = sock.recv(512)
            else:
                print("Don't know command:", cmd)

        # Done with commands, end with a status
        sock.sendall(b"STATUS")
        response = sock.recv(512)
        print(f"eggtimer {pidint} status:", response.decode())

        sock.close()


def fork_timer(sleeptime, message):
    global wakeuptime

    print("Sleeping for", sleeptime, "seconds with message:", message)

    # Return control to the shell before sleeping:
    rc = os.fork()
    if rc:
        sys.exit(0)

    # Trap SIGUSR1
    signal.signal(signal.SIGUSR1, handle_wakeup)

    wakeuptime = time.time() + sleeptime

    time.sleep(sleeptime)

    showAlert(message)


# main: read the runtime arguments.
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Set/manage time reminders",
                             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-c', '--command',  action='append', nargs='+',
                        metavar=('command', 'cmdval'),
                        help="""Commands to query running eggtimers must start
with the PID of the process to be modified.
Examples:
  eggtimer -c 1234 ADD 2
  eggtimer -c 1234 SUBTRACT 60
  eggtimer -c 1234 +10
  eggtimer -c 1234 -40""")
    args, rest = parser.parse_known_args(sys.argv[1:])

    # Three ways of running:
    # 1. eggtimer (no arguments): args.command=None, rest=[]
    # 2. eggtimer 15 blah blah blah
    #    command=None
    #    rest=['15', 'blah', 'blah', 'blah']
    # 3. eggtimer -c 9876 +10 -c 123 +60
    #    args.command=[['9876', '+10'], ['123', '+60']]
    #    rest=[]

    if not args.command and not rest:
        ping_running_eggtimers(None)
        sys.exit(0)

    if not args.command:
        try:
            sleeptime = float(rest[0]) * 60
        except ValueError:
            parser.print_help()
            sys.exit(1)
        message = ' '.join(rest[1:])
        if not message:
            message = "Wake up!"

        fork_timer(sleeptime, message)
        sys.exit(0)

    # We have commands. rest should be empty
    if rest:
        print("Confused -- is this a timer, or a query of running timers?",
              file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # args.command is a list of tuples, like [['9876', '+10'], ['123', '+60']]
    ping_running_eggtimers(args.command)

