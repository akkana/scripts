#!/usr/bin/env python3

# Prettyprint an HTML document (from BeautifulSoup)
# in a customizable way. You can control which tags get newlines
# before them, after them or both.

# BS4's prettify() changes the HTML, possibly adding extra whitespace:
# See https://bugs.launchpad.net/beautifulsoup/+bug/1697296

# Copyright 2018 by Akkana Peck. Share and enjoy under the GPLv2 or later.

import re

#
# Default formatting rules:
#

# Tags to be printed on a line by themselves.
tags_separate_line = [ "html", "head", "body", "p", "br", "ul", "ol", "div",
                       "table", "tr", "title", "meta", "link" ]

# Tags that define a line: they get a newline before start and after end.
# <h1>Here is the page header</h1>
tags_define_line = [ "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6" ]

# Any tag not specified in one of those two list will be printed inline,
# like <b>bold text</b> and <a href="#">links</a>.

def prettyprint(soup,
                separate_line=tags_separate_line,
                define_line=tags_define_line,
                remove_original_newlines=False):
    '''Simple prettyprinter. Add newlines around specified tags.
       No indentation, etc.
       Will preserve all original newlines and only add new ones
       unless remove_original_newlines is specified.
       Returns a string.
    '''

    # Extract empty tags
    for x in soup.find_all():
        if len(x.text) == 0:
            x.extract()

    # Let BeautifulSoup convert to text, then do regexp on the text.
    s = str(soup)
    if remove_original_newlines:
        s = s.replace('\n', '')

    # Replace non-breaking spaces in the unicode string
    # (note: this assumes Python3, so str is unicode):
    s = s.replace("\u00A0", "&nbsp;")

    for tag in separate_line:
        pat = "(<%s.*?>)" % tag
        s = re.sub(pat, r"\n\1\n", s)
        pat = "(</%s>)" % tag
        s = re.sub(pat, r"\n\1\n", s)

    for tag in define_line:
        pat = "(<%s.*?>)" % tag
        s = re.sub(pat, r"\n\1", s)
        pat = "(</%s>)" % tag
        s = re.sub(pat, r"\1\n", s)

    # Now we will have some multiple newlines, so clean those up.
    s = re.sub('\n\n*', '\n', s)

    # If there's no doctype, we probably added a newline before <html>.
    if s.startswith('\n'):
        s = s[1:]

    return s

if __name__ == '__main__':
    from bs4 import BeautifulSoup
    import sys

    for f in sys.argv[1:]:
        with open(f) as fp:
            soup = BeautifulSoup(fp, "lxml")

            pp = prettyprint(soup, remove_original_newlines=True)


