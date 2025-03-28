#!/usr/bin/env python3

"""Trying to define a class (FlexWindow),
   inheriting from tk.Toplevel, that can be either a main window by itself,
   or a secondary window popped up from an app that already has a main window.
"""

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
            print("Calling FlexWindow.reshow()")
            self.win2.reshow("Hello again -- I'm back!")
        else:
            print("Creating a new FlexWindow")
            self.win2 = FlexWindow("Here's a new secondary window")

            # Redefine the wm close button so that it just hides
            # the secondary window
            self.win2.protocol("WM_DELETE_WINDOW", self.win2.hide)


class FlexWindow(tk.Toplevel):
    def __init__(self, message, parent=None):
        # Apparently the self is automatically passed when you call
        # super().__init__()
        # But alternately you could call it with the explicit class name,
        # and in that case you do need to pass self:
        tk.Toplevel.__init__(self)

        frame = tk.Frame(self, parent)
        frame.pack()

        self.label = tk.Label(frame, text=message)
        self.label.pack()
        tk.Button(frame, text="Hide", command=self.hide).pack()

    def hide(self, event=None):
        # iconify makes an icon the windowmanager can show;
        # withdraw hides/unmaps the window without making an icon.
        print("Hiding by withdrawing...")
        self.withdraw()

    def reshow(self, new_msg=None):
        print("Showing an old window again")

        if not new_msg:
            new_msg = "Hi again"
        self.label.config(text=new_msg)

        # deiconify will show a window whether it was withdrawn or iconified
        self.deiconify()


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        mw = FlexWindow("Now I'm primary, not secondary")
        mw._root().mainloop()
    else:
        mw = MainWindow()
        mw.root.mainloop()

