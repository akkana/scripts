#!/usr/bin/env python3

# Initial code from the example at
# https://shkspr.mobi/blog/2022/11/getting-started-with-mastodons-conversations-api/
# https://codeberg.org/edent/Mastodon_Tools

from mastodon import Mastodon
from treelib import Node, Tree
import sys, os

server_url = None
access_token = None

def Usage(exitcode=0):
    print("Usage: mastothread THREAD_ID")
    print()
    print("Requires ~/.config/mastothread including these two lines:")
    print("SERVER = https://your-server-url")
    print("ACCESS_TOKEN = your-access-token")
    sys.exit(exitcode)

# Read access token from ~/.config/mastothread
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


def show_discussion(status):

    conversation = mastodon.status_context(status)

    from pprint import pprint
    pprint(conversation)

    # Are there any ancestors?
    # if len(conversation["ancestors"]) > 0 :
    #    status = conversation["ancestors"][0]
    #    status_id = status["id"]
    #    conversation = mastodon.status_context(status_id)

    tree = Tree()

    tree.create_node(status["content"], status["id"])

    for status in conversation["descendants"] :
        try :
            tree.create_node(status["content"], status["content"],
                             parent=status["in_reply_to_id"])
        except :
            #  If a parent node is missing
            print("Problem adding node to the tree")

    tree.show()


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        Usage()

    mastodon = Mastodon(api_base_url=server_url, access_token=access_token)

    status = mastodon.status(sys.argv[1])

    show_discussion(status)

