#!/usr/bin/env python

# An example of how to do work in a separate thread and send messages to it.

import multiprocessing
import time
import sys

def worker(q):
    print "Starting worker"
    while True:
        print ".",
        sys.stdout.flush()
        time.sleep(2)
        if not q.empty():
            num = q.get(block=False)
            print "Got a message:", num
            if num < 0:
                return

if __name__ == '__main__':
    queue = multiprocessing.Queue()

    p = multiprocessing.Process(target=worker, args=(queue,))
    p.start()

    for i in range(5):
        time.sleep(5)
        queue.put(i)

    queue.put(-1)

    # Wait for the worker to finish
    queue.close()
    queue.join_thread()
    p.join()
