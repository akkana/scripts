#!/usr/bin/env python3

import tkinter as tk

#
# The main window doesn't inherit from tk.Toplevel:
# apparently tk.Tk() does a lot of the same things as Toplevel
# and doing both in the same class can cause problems,
# so Toplevel should only be used for windows after the first one.
#
class MainWindow():
    def __init__(self):
        self.root = tk.Tk()
        frame = tk.Frame(self.root)
        frame.pack()
        okButton = tk.Button(frame, text="Pop Up New Window",
                             command=self.popup_subwindow)
        okButton.pack()
        quitButton = tk.Button(frame, text="Quit",
                               command=frame.quit)
        quitButton.pack()
        self.win2 = None

    def popup_subwindow(self):
        if self.win2:
            print("Calling SecondaryWindow.reshow()")
            self.win2.reshow("Hi again!")
        else:
            print("Creating a new window")
            self.win2 = SecondaryWindow("Here's a new secondary window")


class SecondaryWindow(tk.Toplevel):
    def __init__(self, message):
        super().__init__()
        frame = tk.Frame(self)
        frame.pack()
        self.label = tk.Label(frame, text=message)
        print("Set self.label to", self.label)
        self.label.pack()
        tk.Button(frame, text="Hide", command=self.hide).pack()

    def hide(self, event=None):
        # iconify makes an icon the windowmanager can show;
        # withdraw hides/unmaps the window without making an icon.
        print("Withdrawing...")
        self.withdraw()
        print("self.label is now", self.label)

    def reshow(self, new_msg=None):
        print("Showing an old window again")

        if not new_msg:
            new_msg = "I'm back"
        print("self.label is", self.label)
        self.label.config(text=new_msg)

        # deiconify will show a window whether it was withdrawn or iconified
        self.deiconify()


if __name__ == '__main__':
    mw = MainWindow()
    mw.root.mainloop()

