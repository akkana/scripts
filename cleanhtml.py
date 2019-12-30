#!/usr/bin/env python3

# Clean up HTML and prettyprint it.

from bs4 import BeautifulSoup
import re
import sys

def remove_empty_tags(soup):
    for t in soup.find_all():
        innerhtml = t.text
        # print "tag", t
        # print "innerHTML", innerhtml
        if not innerhtml or not innerhtml.strip():
            t.extract()

def prettyprint(soup):
    """Simple prettyprinter, just add newlines around block nodes.
       No indentation, etc.
       Also get rid of non-breaking spaces (c2 a0).
       Returns a string.
       BS4's prettify() changes the HTML, adding spurious rendered whitespace.
       See https://bugs.launchpad.net/beautifulsoup/+bug/1697296
    """
    s = str(soup)
    print("type s:", type(s), file=sys.stderr)

    # Replace non-breaking spaces in the unicode string
    # (note: this assumes Python3, so str is unicode):
    s = s.replace("\u00A0"," ")

    # Newline after start and before end:
    for tag in ("html", "head", "body"):
        pat = "<%s>" % tag
        s = s.replace(pat, pat + "\n")
        pat = "</%s>" % tag
        s = s.replace(pat, "\n" + pat)

    # Newline before start, leave end alone:
    for tag in ("li",):
        pat = "<%s>" % tag
        s = s.replace(pat, "\n" + pat)
        # s = re.sub(pat, "\n" + pat, s)

    # Newlines both before and after tags:
    for tag in ("p", "br", "br /", "ul", "/ul", "ol", "/ol",
                "div", "/div", "table"):
        pat = "(<%s.*?>)" % tag
        s = re.sub(pat, "\n\\1\n", s)

    # Header patterns:
    s = re.sub("(<h[1-6]>)", "\n\n\\1", s)
    s = re.sub("(</h[1-6]>)", "\\1\n", s)
    return s

def clean_up_html(soup, remove_images=True):
    remove_empty_tags(soup)

    for t in soup.findAll('font'):
        t.replaceWithChildren()
    for t in soup.find_all(class_=re.compile("^m_")):
        t.replaceWithChildren()

    if remove_images:
        for t in soup.findAll("img"):
            t.extract()

    # Remove all inline style tags:
    # for t in soup.findAll(lambda tag: 'style' in tag.attrs):
    for t in soup.findAll(style=True):
        del t["style"]

    return soup

if __name__ == '__main__':
    for f in sys.argv[1:]:
        with open(f) as infp:
            soup = BeautifulSoup(infp, "lxml")
            clean = clean_up_html(soup)
            print(prettyprint(clean))

