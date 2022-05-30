#!/usr/bin/env python3

import sys, os
import time

PIPENAME = "/tmp/namedpipe.pipette"

INPUT = """In Xanadu did Kubla Khan
A stately pleasure dome decree
Where Alph, the sacred river, ran
Through caverns measureless to man
Down to a sunless sea"""


def server():
    """Creates the named pipe and writes to it"""
    if os.path.exists(PIPENAME):
        os.unlink(PIPENAME)

    os.mkfifo(PIPENAME)

    with open(PIPENAME, 'w') as fifo:
        for line in INPUT.splitlines():
            print(line, file=fifo)
            # fifo.write(line)
            fifo.flush()
            print("Wrote", line)
            time.sleep(3)


# Easiest way to read: loop by lines.
def client():
    with open(PIPENAME) as fifo:
        for line in fifo:
            # print("Read:", line)
            sys.stdout.write("Read: " + line)


# If you need more control
def client1():
    with open(PIPENAME, 'r') as fifo:
        while True:
            # fifo.readline() works to read a line.
            # fifo.read(1) works to read a byte at a time
            # as soon as the server has written them.
            # fifo.read() with no size specified blocks until
            # the server has finished and closed the pipe.
            # I don't know if there's a way to read as many bytes
            # as are available in a fifo, whether or not they end
            # with a newline, in a single call.
            data = fifo.readline()
            if not data:
                break
            print("Read", data)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        client1()
    else:
        server()


