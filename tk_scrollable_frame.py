#!/usr/bin/env python3

import sys, os

import tkinter as tk
from tkinter import ttk

server_url = None
access_token = None

WIN_WIDTH = 400
WIN_HEIGHT = 800
FRAME_WIDTH = WIN_WIDTH - 10
FRAME_HEIGHT = 1000
POST_WIDTH = FRAME_WIDTH - 10
LABEL_WIDTH = POST_WIDTH - 20


ROOTBACKGROUND = "lightblue"
POSTBACKGROUND = "yellow"
LABELBACKGROUND = "white"

HAMLET = '''To be, or not to be, that is the question:
Whether 'tis nobler in the mind to suffer
The slings and arrows of outrageous fortune,
Or to take arms against a sea of troubles,
And by opposing end them: to die, to sleep
No more; and by a sleep, to say we end
The heart-ache, and the thousand natural shocks
That Flesh is heir to? 'Tis a consummation
Devoutly to be wished. To die, to sleep,
To sleep, perchance to Dream; aye, there's the rub,
For in that sleep of death, what dreams may come,
When we have shuffled off this mortal coil,
Must give us pause. There's the respect
That makes Calamity of so long life:
For who would bear the Whips and Scorns of time,
The Oppressor's wrong, the proud man's contumely, [F: poore]
The pangs of despised Love, the law’s delay, [F: dispriz’d]
The insolence of office, and the spurns
That patient merit of th'unworthy takes,
When he himself might his Quietus make
With a bare Bodkin? Who would Fardels bear, [F: these Fardels]
To grunt and sweat under a weary life,
But that the dread of something after death,
The undiscovered country, from whose bourn
No traveller returns, puzzles the will,
And makes us rather bear those ills we have,
Than fly to others that we know not of?
Thus conscience does make cowards of us all,
And thus the native hue of Resolution
Is sicklied o'er, with the pale cast of Thought,
And enterprises of great pitch and moment, [F: pith]
With this regard their Currents turn awry, [F: away]
And lose the name of Action. Soft you now,
The fair Ophelia? Nymph, in thy Orisons
Be all my sins remember'd.
'''


class ScrolledWin:
    def __init__(self):
        import tkinter as tk

        self.root = tk.Tk()
        self.root.title("Mastothread")
        self.root.geometry(f'{WIN_WIDTH}x{WIN_HEIGHT}')
        self.root.config(bg=ROOTBACKGROUND)
        self.root.bind('<Control-Key-q>', self.quit)

        # Thanks to https://blog.teclado.com/tkinter-scrollable-frames/
        container = ttk.Frame(self.root)
        self.canvas = tk.Canvas(container, bg="red")
        scrollbar = ttk.Scrollbar(container, orient="vertical",
                                  command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
                                          # width=FRAME_WIDTH,
                                          # height=FRAME_HEIGHT)
        self.scrollable_frame.bind("<Configure>", self.configure_scrollable)
        self.canvas.create_window((0, 0), window=self.scrollable_frame,
                                  anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Create some sub-items for posts
        for line in HAMLET.splitlines():
            post = tk.Frame(self.scrollable_frame, bg=POSTBACKGROUND,
                            width=POST_WIDTH)
            label = tk.Label(post, bg=LABELBACKGROUND,
                             anchor="w", justify=tk.LEFT,
                             wraplength=LABEL_WIDTH,
                             text=' '.join([line]*3))
            label.bind('<Configure>', lambda e: self.label_configure(e, label))
            label.pack(padx=5, pady=5, fill="x", expand=True)
            post.pack(padx=5, pady=5, fill="x", expand=True)
            # post.pack_propagate(0)

        container.pack(fill="both", expand=True)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def quit(self, e):
        self.root.destroy()
        sys.exit(0)

    def label_configure(self, e, label):
        # print("label configure", e)
        label.config(wraplength=label.winfo_width())

    def configure_scrollable(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def show(self):
        self.root.mainloop()


if __name__ == '__main__':
    win = ScrolledWin()
    win.show()
