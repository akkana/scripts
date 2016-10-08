#! /usr/bin/env python

# Simulate the Monty Hall problem
# Copyright Akkana blahblah GPL2orlater blahblah

import random, time

random.seed()

tot = 0
switchwins = 0
staywins = 0

while True:
    # Doors 1-3. Which door has the car?
    cardoor = random.randint(1, 3)

    # Which door do you pick fist?
    firstpick = random.randint(1, 3)

    # Which door does Monty open now? Not the one with the car.
    while True :
        opendoor = random.randint(1, 3)
        if opendoor != cardoor :
            break

    tot += 1
    if firstpick == cardoor :    # should have stayed
        print "  stay",
        staywins += 1
    else :
        print "switch",
        switchwins += 1

    print "   switch % =", int(switchwins * 100 / tot)
    if tot % 1000 == 0:
        print "(%d ...)" % tot
        time.sleep(1)

