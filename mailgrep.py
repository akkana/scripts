#!/usr/bin/env python3

# Grep through one or more mailboxes for a pattern, using normal grep flags.
# Mailboxes must either be all maildir or all mbox, no mixing.
# Requires grepmail to use mbox format.

# Maildir technique adapted from
# https://mutt-users.mutt.narkive.com/pBsMlWya/grepmail-alike-for-maildirs

import subprocess
import shutil
import tempfile
import sys, os


def grep_maildirs(pattern, dirs, flags):
    outstring = subprocess.check_output(["grep", "-lr", *flags,
                                         pattern, *dirs])

    if not outstring:
        return

    matchfiles = outstring.split(b'\n')
    tmpdir = tempfile.mkdtemp(prefix="mailgrep-")

    curdir = os.path.join(tmpdir, "cur").encode()
    os.mkdir(curdir)

    # Mutt needs these two empty directories to believe it's a maildir.
    os.mkdir(os.path.join(tmpdir, "new"))
    os.mkdir(os.path.join(tmpdir, "tmp"))

    for f in matchfiles:
        # Guard against blank lines
        if not f:
            continue
        # f is bytes, curdir is a string. Sigh.
        newfile = os.path.join(curdir, os.path.basename(f))
        shutil.copy2(f, newfile)

    subprocess.call(["mutt", "-Rf", tmpdir])

    shutil.rmtree(tmpdir)


def grep_mboxes(pattern, mboxes, flags):
    outstring = subprocess.check_output(["grepmail", *flags, *mboxes])
    tmp_mbox, tmp_mbox_name = tempfile.mkstemp(prefix="mailgrep-")
    fp = os.fdopen (tmp_mbox, "wb")
    fp.write(outstring)
    fp.close()

    subprocess.call(["mutt", "-Rf", tmp_mbox_name])

    os.unlink(tmp_mbox_name)


def Usage():
    print("Usage:", os.path.basename(sys.argv[0]),
          "[grepflags] PATTERN mailbox [mailbox...]")
    sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        Usage()

    pattern = None

    flags = []
    files = []
    for f in sys.argv[1:]:
        if f.startswith('-'):
            flags.append(f)
        elif not pattern:
            pattern = f
        else:
            files.append(f)

    ismaildir = False
    ismbox = False

    for f in files:
        if not os.path.exists(f):
            print(f, "doesn't exist")
            Usage()

        if os.path.isdir(f):
            ismaildir = True
        else:
            ismbox = True

    if ismaildir and ismbox:
        print("Mailboxes must be all maildir or all mbox")
        Usage()

    if ismaildir:
        grep_maildirs(pattern, files, flags)
    else:
        grep_mboxes(pattern, files, flags)

