#!/usr/bin/env python

import sys, os

# TkInter changed its capitalization between Python versions. Sigh.
if sys.version[:1] == '2':
    import Tkinter as tk
else:
    import tkinter as tk

# Requires: python3-pil.imagetk or python-pil.imagetk
from PIL import ImageTk, Image

imgpath = os.path.expanduser("~/Images/Icons/tux/tux.gif")

labeltxt = """Here is a whole bunch of text.
It has multiple lines in it. It's like a paragraph, almost,
except that it doesn't have anything useful to say."""

class View(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.image = ImageTk.PhotoImage(Image.open(imgpath))
        # The compound= controls where the image is drawn relative to the text.
        b = tk.Label(self, text=labeltxt, image=self.image,
                     justify="left", compound="left")
        b.pack(side="top")

if __name__ == "__main__":
    root = tk.Tk()
    view = View(root)
    view.pack(side="top", fill="both", expand=True)
    root.mainloop()

