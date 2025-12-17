#!/usr/bin/env python3

# Initial code from the example at
# https://shkspr.mobi/blog/2022/11/getting-started-with-mastodons-conversations-api/
# https://codeberg.org/edent/Mastodon_Tools

from mastodon import Mastodon
import sys, os

import tkinter as tk
from tkinter import ttk
import json
from treelib import Node, Tree
from bs4 import BeautifulSoup


server_url = None
access_token = None

WIN_WIDTH = 800
WIN_HEIGHT = 900
FRAME_WIDTH = WIN_WIDTH - 10
FRAME_HEIGHT = 1000              # This isn't actually meaningful
POST_WIDTH = FRAME_WIDTH - 10
LABEL_WIDTH = POST_WIDTH - 20

def Usage(exitcode=0):
    print("Usage: mastothread THREAD_ID")
    print()
    print("Requires ~/.config/mastothread including these two lines:")
    print("SERVER = https://your-server-url")
    print("ACCESS_TOKEN = your-access-token")
    sys.exit(exitcode)


def init_mastodon():
    """Read server and access token from ~/.config/mastothread.
       Return server_url and access_token.
    """
    try:
        configfile = os.path.expanduser('~/.config/mastothread')
        with open(configfile) as fp:
            for line in fp:
                name, val = [ s.strip() for s in line.split('=') ]
                # print("name", name, "val", val)
                if name == 'ACCESS_TOKEN':
                    access_token = val
                elif name == "SERVER":
                    server_url = val
    except Exception as e:
        print("Couldn't get Mastodon access token and server:", e)
        Usage(1)

    if not server_url:
        print("No Mastodon server specified")
        Usage(1)

    if not access_token:
        print("No Mastodon access token")
        Usage(1)

    return server_url, access_token


ROOTBACKGROUND = "lightblue"
POSTBACKGROUND = "yellow"
LABELBACKGROUND = "white"


class MastoThreadWin:
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

        container.pack(fill="both", expand=True)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def add_item(self, statustext):
        post = tk.Frame(self.scrollable_frame, bg=POSTBACKGROUND,
                        width=POST_WIDTH)
        label = tk.Label(post, bg=LABELBACKGROUND,
                         anchor="w", justify=tk.LEFT,
                         wraplength=LABEL_WIDTH,
                         text=statustext)
        label.bind('<Configure>', lambda e: self.label_configure(e, label))
        label.pack(padx=5, pady=5, fill="x", expand=True)
        post.pack(padx=5, pady=5, fill="x", expand=True)

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


def clean_html_crap(htmlcrap):
    """Mastodon status are full of crap like
       <p><span class="h-card" translate="no"><a href="USER_URL" class="u-url mention" rel="nofollow noopener" target="_blank">@<span>username</span></a></span>
       so remove anything between angle brackets ... which is frustrating
       because what if someone actually posts something involving
       angle brackets?
    """
    return BeautifulSoup(htmlcrap).text


def show_discussion(status, threadwin):

    jsonfile = 'convo.json'
    if os.path.exists(jsonfile):
        with open(jsonfile) as jfp:
            print("Reading from", jsonfile)
            conversation = json.load(jfp)
    else:
        conversation = mastodon.status_context(status)

        with open(jsonfile, 'w') as jfp:
            json.dump(conversation, jfp, indent=4, default=str)
            print("wrote conversation to", jsonfile)

    # Are there any ancestors?
    # if len(conversation["ancestors"]) > 0:
    #    status = conversation["ancestors"][0]
    #    status_id = status["id"]
    #    conversation = mastodon.status_context(status_id)

    # First save the conversation as a tree,
    # so statuses can be displayed in depth-first order.
    tree = Tree()
    tree.create_node(status["content"], status["id"])

    for status in conversation["descendants"]:
        try:
            tree.create_node(status["content"], status["id"],
                             parent=status["in_reply_to_id"])
        except Exception as e:
            # If a parent node is missing
            print("Problem adding node to the tree:", e)
            # saved_statuses.append(status)

    # tree.show()

    # Depth-first traversal:
    for id in tree.expand_tree():
        # tree[id] is type <class 'treelib.node.Node'>
        # use tag to get to the text in it
        print("id", id, "content", tree[id].tag, "type", type(tree[id]))
        try:
            threadwin.add_item(clean_html_crap(tree[id].tag))
        except Exception as e:
            print("Couldn't add_item for", tree[id].tag, "because:", e)

    print("Done adding items")


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        Usage()

    threadwin = MastoThreadWin()

    jsonfile = 'mastopost.json'
    if os.path.exists(jsonfile):
        with open(jsonfile) as jfp:
            print("Reading from", jsonfile)
            status = json.load(jfp)
    else:
        server_url, access_token = init_mastodon()
        mastodon = Mastodon(api_base_url=server_url, access_token=access_token)
        status = mastodon.status(sys.argv[1])
        with open(jsonfile, 'w') as jfp:
            json.dump(status, jfp, indent=4, default=str)
            print("wrote to", jsonfile)

    show_discussion(status, threadwin)

    threadwin.show()
