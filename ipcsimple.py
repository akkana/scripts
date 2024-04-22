#!/usr/bin/env python3

# Simple inter-process communication:
# communicate with other processes via signals and/or Unix-domain sockets.


import signal
import socket
import time
import os, sys


def list_procs(procname, uid=None):
    """Iterator: Find all running processes matching procname.
       Optionally, must match the given UID.
       Yield int pids.
    """

    procnamelist = [ procname, procname + ".py" ]
    pidlist = []
    for pid in os.listdir("/proc"):
        # Skip the current process' PID
        try:
            pidint = int(pid)
        except:
            continue
        if pidint == os.getpid():
            continue

        if uid != None:
            uids = get_uids(pid)
            if uids and int(uids[0]) != os.getuid():
                continue

        if is_target_proc(pid, procnamelist):
            yield(pidint)


def is_target_proc(pid, procnames):
    """Does the given pid match any of the process names?
       pid is a STRING process ID; procnames is a list.
    """
    try:
        # Look for processes named procname or procname.py
        with open(os.path.join("/proc", str(pid), "cmdline")) as fp:
            cmdline = fp.read().split('\0')

            # Is it a Python process? Remove python and, possibly, -m
            if cmdline[0].endswith("python") or cmdline[0].endswith("python3"):
                cmdline = cmdline[1:]
                if cmdline and cmdline[0] == '-m':
                    cmdline = cmdline[1:]
            if not cmdline:
                return False

            for procname in procnames:
                if cmdline[0].endswith(procname):
                    return True
            return False
    except:
        # Likely a non/integer directory or file in /proc
        return False


def get_uids(pid):
    """Return the list of UIDs for the given process ID:
       Real, effective, saved set, and filesystem UIDs
       (see proc(5) man page).
    """
    try:
        with open(f"/proc/{pid}/status") as fp:
            for line in fp:
                if not line.startswith('Uid:\t'):
                    continue
                return line.split()[1:]

    except FileNotFoundError:
        pass

    return []


def kill_instances(procname):
    for pid in list_procs(procname, os.getuid()):
        os.kill(int(pid), signal.SIGKILL)


ipc_handler = None

def set_ipc_handler(ipc_handler_fcn):
    """Run this from the long-running process, passing in a function
       that the long-running process will invoke to talk over a socket.
       Data from the socket will be passed to the ipc_handler as bytes.
    """
    global ipc_handler
    ipc_handler = ipc_handler_fcn

    # Trap SIGUSR1
    signal.signal(signal.SIGUSR1, ipc_communicate)


def ping_running_process(pidint, sendstring=None):
    """Wake up a running process with a SIGUSR1, send some data to it,
       read and return the response.
       pid must be an int.
       sendstring may be string or bytes.
    """
    # Wake up the process and tell it to create a socket
    os.kill(pidint, signal.SIGUSR1)

    # Look for Unix-domain socket named /tmp/eggtimer.[pid]
    # May have to wait a little while for it to be created,
    # but don't wait forever.
    sockname = f"/tmp/ipcsimple.{pidint}"
    for i in range(10):
        if os.path.exists(sockname):
            break
        time.sleep(.25)

    if not os.path.exists(sockname):
        print("Couldn't open socket", sockname)
        return None

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(sockname)

    if sendstring:
        sock.sendall(bytes(sendstring))

    response = sock.recv(512)
    return response.decode()


def ipc_communicate(signal, frame):
    """On waking up via a signal, set up a socket to communicate
       with whoever caused the wakeup, and write to it using ipc_handler_fcn.
    """
    if not ipc_handler:
        print("No ipc handler registered, so doing nothing")
        return

    # Set up a socket for full-duplex communication:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sockname = f"/tmp/ipcsimple.{os.getpid()}"
    if not os.path.exists(sockname):
        sock.bind(sockname)
        sock.listen(1)
        conn, addr = sock.accept()

    sendstr = ipc_handler()[0].replace('\n', ' ')
    conn.sendall(sendstr.encode())
    os.unlink(sockname)


if __name__ == '__main__':
    print("getpid:", os.getpid())

    uid = os.getuid()
    procs = list(list_procs("breaktime", uid=uid))

    for proc in procs:
        print(proc, ":", get_uids(proc))

