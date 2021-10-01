#!/usr/bin/env python3

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import sys, os


# Base of wikipedia for the desired language
wikibase = "https://en.wikipedia.org/"


# links inside any of these tags will be ignored
ignore_parents = [ "ul", "table" ]

# links with these classes, or inside anything with these classes,
# will be ignored
ignore_classes = [ "image", "thumb", "hatnote",  "flaggedrevs",
                   "mw-indicator", "IPA" ]


def firstlink(pageurl):
    """Return the href from the first link of a wikipedia page"""
    r = requests.get(pageurl)
    soup = BeautifulSoup(r.text, "lxml")

    # XXX Enumerate only because knowing i (which link matched)
    # is interesting during debugging.
    for i, link in enumerate(soup.find_all("a", href=True)):
        # Don't count internal page anchros like #ms-head
        href = link.get("href")
        if href.startswith("#"):
            continue
        # Don't count disambiguation links
        if "disambiguation" in href:
            continue

        # Not interested unless the link is to another wikipedia article
        if not href.startswith("/wiki/"):
            continue

        # Is the link inside a list, table, or div with a class like hatnote??
        if should_skip(link, ignore_parents, ignore_classes):
            continue

        # Return link, term (relative link), text
        return (urljoin(wikibase, link.get("href")),
                link.get("href"),
                link.text)


def should_skip(tag, parenttags, classpats):
    """Is the given linktag (tag object) a child of any of the given tags,
       or a child of any tag with a class containing any of the given classpats?
       parenttags is a list of str tag names.
    """
    while True:
        # Got to the top?
        if tag.name == "body":
            return False

        for name in parenttags:
            if tag.name == name:
                return True

        for classpat in classpats:
            classes = tag.get("class")
            if classes:
                for c in classes:
                    if classpat in c:
                        return True

        # This shouldn't happen if we stop at <body>,
        # but keep it in for a while, just in case.
        try:
            tag = tag.parent
        except Exception as e:
            print("eek, no parent for", tag.name)
            print(traceback.format_exc())
            sys.exit(0)
            # return False



def follow_links(term, terminator, interactive=False):
    """Follow the first link from the body of a term's wikipedia page
       and then continue to follow the first link of each subsequent page
       until finally arriving at the expected terminator page.
       The theory is that the chain always gets to "Philosophy".
       Return a list of triples: (term, absurl, link_text)
    """
    linklist = []
    link = wikibase + 'wiki/' + term
    hops = 0
    text = term
    while True:
        if interactive:
            print("%3d %-23s %s" % (hops, text, link))
            sys.stdout.flush()

        if os.path.basename(link) == terminator:
            return linklist
        hops += 1
        link, term, text = firstlink(link)
        linklist.append((link, term, text))


if __name__ == '__main__':
    try:
        for term in sys.argv[1:]:
            linklist = follow_links(term.replace(' ', '_'), "Philosophy",
                                    interactive=True)

    except KeyboardInterrupt:
        print("Interrupt")


