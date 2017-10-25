#!/usr/bin/env python

# Based on irw.c, https://github.com/aldebaran/lirc/blob/master/tools/irw.c
# Python AF_UNIX socket example: https://pymotw.com/2/socket/uds.html

import socket
import sys

SOCKPATH = "/var/run/lirc/lircd"

sock = None

def init_irw():
    global sock
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    print ('starting up on %s' % SOCKPATH)
    try:
        sock.connect(SOCKPATH)
    except socket.error, msg:
        print >>sys.stderr, msg
        sys.exit(1)

def next_key():
    '''Get the next key pressed. Return keyname, updown.
    '''
    while True:
        data = sock.recv(128)
        # print("Data: " + data)
        data = data.strip()
        if data:
            break

    words = data.split()
    return words[2], words[1]

if __name__ == '__main__':
    init_irw()

    while True:
        keyname, updown = next_key()
        print('%s (%s)' % (keyname, updown))

