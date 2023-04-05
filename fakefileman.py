#!/usr/bin/env python3

"""fakefileman: a fake file manager
   that looks like a file manager to the XDG desktop system,
   but actually gives you a shell in a terminal window.

   To use this, link this script to "fileman" somewhere in your PATH,
   then create ~/.local/share/applications/fakefileman.desktop
   containing something like this:

[Desktop Entry]
Version=1.0
Name=Fake File Manager
Comment=Bring up a terminal in the directory indicated by the first argument
Exec=xterm -e fakefileman %F
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Application;
MimeType=inode/directory;

    You might also have to edit ~/.local/share/applications/mimeinfo.cache
    and add this line:

inode/directory=fakefileman.desktop;

    In theory  mimeinfo.cache should be autogenerated,
    but I'm not sure how reliable that is.
"""

import sys, os
import subprocess

try:
    if os.path.isdir(sys.argv[1]):
        os.chdir(sys.argv[1])
        print("Current directory:", sys.argv[1])

        if len(sys.argv) > 2:
            print("Other arguments:", sys.argv[2:])

    else:
        print("Arguments:", sys.argv[1:])

except Exception as e:
    print("Couldn't cd", sys.argv[1], ":", e)

print()

subprocess.call(["zsh"])



