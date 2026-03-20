#!/usr/bin/env python3

"""A mini protocol for two hosts to discover each other on a LAN,
   for peer-to-peer networking,
   based on broadcast and reply ports they both know.
"""

# Copyright 2026 by Akkana Peck, share and enjoy under the GPLv2 or later.

import socket
import time
import getpass
import random


USERNAME = getpass.getuser()
MY_USER_BYTES = USERNAME.encode()

BROADCAST_PORT = 28999
REPLY_PORT = 28989


def get_my_ip():
    addrs = socket.gethostbyname_ex(socket.gethostname())[2]
    if not addrs:
        return None

    for ip in addrs:
        # Skip localhost, 127.0.0.1
        if ip.startswith('127'):
            continue
        return ip

    # if we get here, all addrs are localhost.
    return addrs[0]


MY_IP = get_my_ip()
MY_IP_BYTES = MY_IP.encode()
MY_ID_BYTES = b'uppity||%s||%s' % (MY_IP_BYTES, MY_USER_BYTES)

other_host = None


# Server routine
def broadcast_ip():
    global other_host

    broadcast_socket = socket.socket(socket.AF_INET,
                                     socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # broadcast mode
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Set a timeout so the socket does not block
    # indefinitely when trying to receive data.
    broadcast_socket.settimeout(random.randint(5, 10))

    broadcast_socket.sendto(MY_ID_BYTES,
                            ('<broadcast>', BROADCAST_PORT))
    print("message broadcast, listening for responses")

    #
    # See if there are any responses
    #
    response_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    response_socket.settimeout(10)
    # bind the socket to a public host, and a well-known port
    response_socket.bind((MY_IP, REPLY_PORT))
    response_socket.listen(1)
    try:
        (conn, address) = response_socket.accept()
        conn.settimeout(random.randint(5, 10))
        # data, addr = response_socket.recvfrom(1024)
        data = conn.recv(1024)
        print("Got a response! '%s'" % (data))
        try:
            proto, clientip, remoteuser = data.split(b'||')
        except:
            print("Bad protocol, not three parts:", data)
            return False
        other_host = { 'ip': clientip.decode(), "user": remoteuser.decode() }
        return True
    except TimeoutError:
        print("Timeout, didn't get any responses")
        return False


# Client routine
def listen_for_servers():
    global other_host

    client_socket = socket.socket(socket.AF_INET,
                                  socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Receive broadcasts
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    client_socket.settimeout(random.randint(5, 10))

    client_socket.bind(("", BROADCAST_PORT))

    try:
        data, addr = client_socket.recvfrom(1024)
        print("received: '%s' from %s" % (data, addr))
    except TimeoutError:
        print("Timed out, returning")
        return False

    # The server sends something like: b'uppity||192.168.1.2||username'
    if not data.startswith(b'uppity||'):
        print("Bad protocol,", data)
        return False
    try:
        proto, serverip, remoteuser = data.split(b'||')
    except:
        print("Bad protocol, not three parts:", data)
        return False

    # Reply to the server
    responding_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    responding_socket.settimeout(10)
    # now connect to the web server on port 80 - the normal http port
    try:
        responding_socket.connect((serverip, REPLY_PORT))
        responding_socket.send(MY_ID_BYTES)
        print("sent a client response!", MY_ID_BYTES)
        other_host = { 'ip': serverip.decode(), "user": remoteuser.decode() }
        return True
    except TimeoutError:
        print("Timed out trying to send a response")
        return False


if __name__ == '__main__':
    # Alternate between broadcasting our IP, listening for an answer,
    # and listening for another node that's broadcasting its IP,
    # with random times.

    while True:
        print("\nBroadcasting my IP")
        if broadcast_ip():
            print("broadcast_ip() returned True!")
            break
        time.sleep(random.randint(0, 10))
        print("\nNow listening for servers")
        if listen_for_servers():
            print("listen_for_servers() returned True!")
            break
        time.sleep(random.randint(0, 10))

    print("Woohoo, some communication happened")
    print("Remote host is %s, user %s" % (other_host['ip'], other_host['user']))
