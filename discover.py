#!/usr/bin/env python3

"""A mini protocol for two hosts to discover each other on a LAN,
   for peer-to-peer networking.

   Alternate between broadcasting and listening for other machines
   that might be broadcasting, with a random timeout so eventually
   one will be broadcasting at the same time the other is listening.
"""

import socket
import time
import random


BROADCAST_PORT = 28999
REPLY_PORT     = BROADCAST_PORT


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

MESSAGE_BYTES = b'discovery||%s' % MY_IP_BYTES

other_host = None


def broadcast():
    """Send out a broadcast on BROADCAST_PORT,
       then listen for replies on REPLY_PORT.
       Return True and save details of the other machine if a valid reply
       was seen, else return False.
    """
    global other_host

    broadcast_socket = socket.socket(socket.AF_INET,
                                     socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # broadcast mode
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Set a timeout so the broadcast doesn't last forever
    # broadcast_socket.settimeout(random.randint(5, 10))

    broadcast_socket.sendto(MESSAGE_BYTES, ('<broadcast>', BROADCAST_PORT))

    # Does the socket need to be shut down afterward?
    # broadcast_socket.shutdown(socket.SHUT_RDWR)
    # broadcast_socket.close()

    print("message broadcast, listening for responses on port", REPLY_PORT)

    #
    # See if there are any responses
    #
    response_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    response_socket.settimeout(random.randint(5, 10))
    # bind the socket to a public host, and a well-known port
    # This sometimes raises OSError: [Errno 98] Address already in use
    response_socket.bind((MY_IP, REPLY_PORT))
    response_socket.listen(1)
    try:
        (conn, address) = response_socket.accept()
        conn.settimeout(random.randint(5, 10))
        # data, addr = response_socket.recvfrom(1024)
        data = conn.recv(1024)
    except TimeoutError:
        print("Timeout, didn't get any responses")
        return False

    print("Got a response! '%s'" % (data))
    try:
        proto, clientip = data.split(b'||')
    except ValueError:
        print("Bad protocol:", data)
        return False
    other_host = { 'ip': clientip.decode() }
    return True

    # response_socket.shutdown(socket.SHUT_RDWR)
    # response_socket.close()


def listen_for_broadcasters():
    """Listen for broadcasts on BROADCAST_PORT.
       If one is seen, reply on REPLY_PORT, save the details of the other
       machine and return True.
       Otherwise, return False.
    """
    global other_host

    # Listen on the BROADCAST_PORT
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

    # The server sends something like: b'discovery||192.168.1.2'
    if not data.startswith(b'discovery||'):
        print("Bad protocol,", data)
        return False
    try:
        proto, serverip = data.split(b'||')
    except:
        print("Bad protocol:", data)
        return False

    # Reply to the server, using the REPLY_PORT
    print("Sending a reply on port", REPLY_PORT)
    responding_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    responding_socket.settimeout(10)
    # now connect to the web server on port 80 - the normal http port
    try:
        responding_socket.connect((serverip, REPLY_PORT))
        responding_socket.send(MESSAGE_BYTES)
        print("sent a client response:", MESSAGE_BYTES)
        other_host = { 'ip': serverip.decode() }
        return True
    except TimeoutError:
        print("Timed out trying to send a response")
        return False


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        while True:
            if sys.argv[1] == 'broadcast':
                broadcast()
            elif sys.argv[1] == 'listen':
                listen_for_broadcasters()

    # By default, alternate between broadcasting
    # and listening for another node that's broadcasting
    while True:
        print("\nBroadcasting")
        if broadcast():
            print("broadcast_ip() returned True!")
            break
        # time.sleep(random.randint(0, 10))

        print("\nNow listening for broadcasters")
        if listen_for_broadcasters():
            print("listen_for_broadcasters() returned True!")
            break
        # time.sleep(random.randint(0, 10))

    print("Woohoo, some communication happened")
    print("Remote host is %s" % (other_host['ip']))
