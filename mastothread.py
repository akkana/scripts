#!/usr/bin/env python3

# Initial code from the example at
# https://shkspr.mobi/blog/2022/11/getting-started-with-mastodons-conversations-api/
# https://codeberg.org/edent/Mastodon_Tools

from mastodon import Mastodon
import sys, os

import tkinter as tk
# PhotoImage only supports an incredibly limited set of formats
from PIL import Image, ImageTk

import json
from treelib import Tree
from bs4 import BeautifulSoup
import re

# For downloading images:
from requests_futures.sessions import FuturesSession
from concurrent.futures import ThreadPoolExecutor
import functools

from datetime import datetime
import dateutil.parser


server_url = None
access_token = None

WIN_WIDTH = 800
WIN_HEIGHT = 900
POST_WIDTH = WIN_WIDTH - 20
LABEL_WIDTH = POST_WIDTH - 50

SFBACKGROUND = "white"
POSTBACKGROUND = "white"
AUTHORBACKGROUND = "#eeffff"
ROOTBACKGROUND = "lightblue"    # not normally visible
CANVASBACKGROUND = "#eeffee"    # not normally visible
CONTAINERBACKGROUND = 'yellow'  # not normally visible
TWEENPOSTSBACKGROUND = '#f3f3f3'

SIMPLETIMEFMT = '%H:%M  %b %d'


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


CACHEDIR = os.path.expanduser("~/.cache/mastothread")

# For mapping URLs to filenames: these are chars not allowed in cache filenames
BADCHARS = re.compile(r'''['\"\(\)&!:\/ ]''')


class MastoThreadWin:
    def __init__(self):
        self.numitems = 0

        # Images in Tk labels are garbage collected and not saved,
        # so they need to be saved somewhere else.
        self.images = []

        self.downloader = \
            FuturesSession(executor=ThreadPoolExecutor(max_workers=6))
        # Don't add a response hook here, because there's no documentataion
        # on how to pass extra arguments to the hook,
        # even though the hook example has args and kwargs.
        # self.downloader.hooks['response'] = self.response_hook

        # Make the UI
        self.root = tk.Tk()
        self.root.title("Mastothread")
        self.root.geometry(f'{WIN_WIDTH}x{WIN_HEIGHT}')
        self.root.config(bg=ROOTBACKGROUND)
        self.root.bind('<Control-Key-q>', self.quit)

        # Make a bar across the top
        topbar = tk.Frame(self.root)
        tk.Label(topbar, text='Last refreshed:').pack(side=tk.LEFT, padx=5)
        self.last_refreshed_label = tk.Label(topbar)
        self.update_refresh_label()
        self.last_refreshed_label.pack(side=tk.LEFT, padx=5)
        button = tk.Button(topbar, text="Refresh", command=self.refresh)
        button.pack(side=tk.RIGHT, padx=5)
        topbar.pack(fill=tk.X, expand=False)

        # Thanks to https://blog.teclado.com/tkinter-scrollable-frames/
        container = tk.Frame(self.root, bg=CONTAINERBACKGROUND)
        self.canvas = tk.Canvas(container, bg=CANVASBACKGROUND)
        scrollbar = tk.Scrollbar(container, orient="vertical",
                                 command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=TWEENPOSTSBACKGROUND)
        self.scrollable_frame.bind("<Configure>", self.configure_scrollable)
        self.canvas.create_window((0, 0), window=self.scrollable_frame,
                                  anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind_all("<Key-space>",
                             lambda e: self.canvas.yview_scroll(1, "pages"))
        self.canvas.bind_all("<Next>",
                             lambda e: self.canvas.yview_scroll(1, "pages"))
        self.canvas.bind_all("<Prior>",
                             lambda e: self.canvas.yview_scroll(-1, "pages"))
        # Binding <MouseWheel>" does nothing, either on the root or the canvas
        self.canvas.bind_all("<Button-5>",   # Linux scroll down
                             lambda e: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind_all("<Button-4>",   # Linux scroll up
                             lambda e: self.canvas.yview_scroll(-1, "units"))


        container.pack(fill="both", expand=True)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def add_item(self, status, indent=0):
        posttime = dateutil.parser.parse(status['created_at'])

        postframe = tk.Frame(self.scrollable_frame, bg=SFBACKGROUND,
                             padx=indent,
                             width=POST_WIDTH)
        authorlabel = tk.Label(postframe, bg=AUTHORBACKGROUND,
                               anchor="w", justify=tk.LEFT,
                               text=self.post_author(status) + "         "
                                 + posttime.astimezone().strftime(SIMPLETIMEFMT))
        postlabel = tk.Label(postframe, bg=POSTBACKGROUND,
                             anchor="w", justify=tk.LEFT,
                             wraplength=LABEL_WIDTH,
                             text=self.post_text(status))
        postlabel.bind('<Configure>',
                       lambda e: self.label_configure(e, postlabel))

        authorlabel.grid(row=0, column=0, sticky='WENS')
        postlabel.grid(row=1, column=0, sticky='WENS')

        # Add images, if any
        if status['media_attachments']:
            imgframe = tk.Frame(postframe)
            for attachment in status['media_attachments']:
                imgfilename = os.path.join(CACHEDIR,
                                           self.url_to_filename(
                                               attachment['preview_url']))
                if os.path.exists(imgfilename):
                    self.add_preview_image(imgfilename, imgframe)
                else:
                    print("Requesting", attachment['preview_url'], '->', imgfilename)
                    self.downloader.get(attachment['preview_url'],
                                        hooks={'response': functools.partial(
                                            self.response_hook,
                                            imgframe=imgframe,
                                            imgfilename=imgfilename
                                        )
                                               })

            imgframe.grid(row=2, column=0)

        # The padx=0 in the next line doesn't help, there's still big padding
        # at the right edge of the scrollable frame
        postframe.grid(row=self.numitems, column=0, sticky='WENS', padx=0, pady=5)
        self.numitems += 1

    @staticmethod
    def url_to_filename(url):
        return BADCHARS.sub('', url)

    def add_preview_image(self, imgfilename, imgframe):
        # print("Trying to show", imgfilename)
        image = Image.open(imgfilename)
        photoimage = ImageTk.PhotoImage(image)
        self.images.append(photoimage)
        imagelabel = tk.Label(imgframe, image=photoimage)
        imagelabel.pack()

    def response_hook(self, response, *args, **kwargs):
        """When the FuturesSession completes downloading an image, show it.
           The standard response_hook example has *args, **kwargs
           in addition to response,
           but nobody anywhere seems to know what these are for or
           how to use them.
        """
        # There's no exception handling in the response hook: if anything
        # goes wrong it just silently does nothing.
        # So try to catch all errors.
        try:
            print("response_hook, downloaded", response.url, "kwargs =", kwargs)
            if response.status_code != 200:
                print("Error: status", response.status_code, "on", response.url)
                # XXX should check response, and maybe retry
                # in which case it shouldn't go on failed_download_urls
                self.num_failed_downloads += 1
                self.last_failed_download_time = time.time()
                self.failed_download_urls[response.url] = \
                    self.last_failed_download_time
                self.urls_queued.remove(response.url)
                return

            # Is the response an image?
            try:
                if not response.headers['Content-Type'].startswith('image/'):
                    if self.mapwin.controller.Debug:
                        print("%s not an image: Content-Type %s"
                              % (response.url,
                                 response.headers['Content-Type']))
                    self.num_failed_downloads += 1
                    self.last_failed_download_time = time.time()
                    return
            except:
                print("No Content-Type in headers for", response.url)
                # Perhaps that's not a problem and it's okay to continue

            print("It's an image, content-type is", response.headers['Content-Type'])
            # Write to disk
            if not os.path.exists(CACHEDIR):
                os.mkdir(CACHEDIR)
            print("Trying to write", kwargs['imgfilename'])
            with open(kwargs['imgfilename'], 'wb') as tilefp:
                content = response.content
                tilefp.write(content)

            # Display it
            self.add_preview_image(kwargs['imgfilename'], kwargs['imgframe'])

        except Exception as e:
            print("Whoops!", e)
            return

    @staticmethod
    def clean_html_crap(htmlcrap):
        """Mastodon status are full of crap like
           <p><span class="h-card" translate="no"><a href="USER_URL" class="u-url mention" rel="nofollow noopener" target="_blank">@<span>username</span></a></span>
           so remove anything between angle brackets ... which is frustrating
           because what if someone actually posts something involving
           angle brackets?
        """
        return BeautifulSoup(htmlcrap, features='lxml').text

    @staticmethod
    def post_text(status):
        return MastoThreadWin.clean_html_crap(status['content'])

    @staticmethod
    def post_author(status):
        return f"{status['account']['username']} ({status['account']['acct']})"

    def quit(self, e):
        self.root.destroy()
        sys.exit(0)

    def label_configure(self, e, label):
        # print("label configure", e, "wrapping to", label.winfo_width())
        label.config(wraplength=label.winfo_width())

    def configure_scrollable(self, e):
        # print("configure_scrollable", e)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mousewheel(self, e):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def show(self):
        self.root.mainloop()

    def update_refresh_label(self):
        self.last_refreshed_label.configure(
            text = datetime.now().strftime(SIMPLETIMEFMT))

    def refresh(self):
        print("Would refresh if I knew how")

    def show_discussion(self, statusid):
        """Add the discussion to a tree, and then add tree entries
           to the thread window.
        """
        jsonfile = 'post.json'
        if os.path.exists(jsonfile):
            with open(jsonfile) as jfp:
                print("Reading from", jsonfile)
                root_status = json.load(jfp)
        else:
            server_url, access_token = init_mastodon()
            mastodon = Mastodon(api_base_url=server_url, access_token=access_token)
            root_status = mastodon.status(statusid)
            with open(jsonfile, 'w') as jfp:
                json.dump(status, jfp, indent=4, default=str)
                print("wrote to", jsonfile)

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
        # Start with the top parent.
        tree = Tree()
        tree.create_node("Data Node", root_status["id"], data=root_status)

        # For testing, it helps to limit the number of entries
        num_entries = 0
        MAX_ENTRIES = 0
        for status in conversation["descendants"]:
            try:
                tree.create_node("Data Node", status["id"],
                                 data=status,
                                 parent=status["in_reply_to_id"])
                if MAX_ENTRIES and num_entries > MAX_ENTRIES:
                    break
                num_entries += 1
            except Exception as e:
                # If a parent node is missing
                print("Problem adding node to the tree:", e)
                # saved_statuses.append(status)

        # tree.show()

        # Depth-first traversal:
        for id in tree.expand_tree():
            # tree[id] is type <class 'treelib.node.Node'>
            # use tag to get to the text in it
            # print("id", id, "content", tree[id].tag, "type", type(tree[id]))
            try:
                # Indent according to depth in the thread
                self.add_item(tree[id].data,
                              indent=30 * tree.depth(tree[id]))
            except Exception as e:
                print("Couldn't add_item for", id, "because:", e)

        print("Done adding items")


def Usage(exitcode=0):
    print("Usage: mastothread THREAD_ID")
    print()
    print("Requires ~/.config/mastothread including these two lines:")
    print("SERVER = https://your-server-url")
    print("ACCESS_TOKEN = your-access-token")
    sys.exit(exitcode)


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        Usage()

    threadwin = MastoThreadWin()

    threadwin.show_discussion(sys.argv[1])

    threadwin.show()
