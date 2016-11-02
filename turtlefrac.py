#!/usr/bin/env python

import turtle
import time
import sys

whichcolor = 0
colors = [ "black", "white" ]

def triangle(side):
    """Draw an equilateral triangle with the point on the current point,
       the base in the direction of the current heading.
    """
    turtle.left(30)
    turtle.forward(side)
    turtle.right(120)
    turtle.forward(side)
    turtle.right(120)
    turtle.forward(side)

def Sierpinski(side, steps):
    """Draw a Sierpinski triangle fractal, recursing the given number of steps.
       Assume we're starting from a black triangle of with sides of size side*2,
       point down, with the turtle at the bottom point.
    """
    if not steps:
        return

    # Clear a white triangle in the center.
    turtle.setheading(120)
    turtle.penup()
    turtle.forward(side)

    turtle.pendown()
    turtle.fill(True)
    turtle.fillcolor("white")
    turtle.right(120)
    turtle.forward(side)
    turtle.left(120)
    turtle.forward(side)
    turtle.left(120)
    turtle.forward(side)
    turtle.fill(False)

    # For each of the black sub-triangles left, run recursively.
    Sierpinski(side/2, steps-1)
    turtle.setheading(0)
    turtle.penup()
    turtle.forward(side)
    Sierpinski(side/2, steps-1)
    turtle.setheading(240)
    turtle.penup()
    turtle.forward(side)
    Sierpinski(side/2, steps-1)

turtle.speed(0)
turtle.setheading(270)
turtle.penup()
turtle.forward(200)
turtle.setheading(90)

turtle.fillcolor("black")
turtle.fill(True)
triangle(500)
turtle.fill(False)

if len(sys.argv) <= 1:
    steps = 5
else:
    steps = int(sys.argv[1])
Sierpinski(250, steps)

turtle.mainloop()
