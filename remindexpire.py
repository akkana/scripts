#!/usr/bin/env python3

# Read a *nix "remind" file in to REMIND_DIR/remind.txt,
# Examine all events between lines
# "# Current" and "# End Current".
# If the date (assumed to be the current year if year isn't specified)
# is in the past, archive that line to REMIND_DIR/archived.txt
# and remove it from remind.txt.


from datetime import date
import os, sys


months = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ]

REMIND_DIR = None

DEBUG = False


def keep_line(line):
    """Analyze a line (already stripped) from a remind file.
       Return keep, linedate where keep is:
           False if it's a date in the past
           True if it's not a date line, or is in the present/future
       and linedate is the date parsed from the line, or None.
    """
    today = date.today()

    # First two words are day month. Third can be year but isn't always.
    # 6 Jan 2024
    line = line.strip()
    if line.startswith('#'):
        return True, None
    words = line.split()
    if words[0] == "REM":
        words = words[1:]

    try:
        mday = int(words[0])
    except:
        # Not a date, probably a comment. Keep it.
        if DEBUG:
            print("not a day:", line, file=sys.stderr)
        return True, None

    try:
        month = words[1][:3]
        month = int(months.index(month)) + 1
    except:
        if DEBUG:
            print("not a month:", line, file=sys.stderr)
        return True, None

    try:
        year = int(words[2])
    except:
        year = today.year

    if DEBUG:
        print(year, month, mday, "<--", line, file=sys.stderr)
    linedate = date(year, month, mday)
    if linedate < today:
        return False, linedate
    return True, linedate


remind_filename = None
save_name = None
archive_name = None
save_fp = None
archive_fp = None

archived_last = False


def save_line(line):
    global save_fp, archived_last
    if not save_fp:
        save_fp = open(save_name, "w")
    save_fp.write(line)
    archived_last = False


def archive_line(line, linedate=None):
    global archive_fp, archived_last
    if not archive_fp:
        archive_fp = open(archive_name, "a")
    if linedate:
        archive_fp.write("%s || %s\n" % (line.strip('\n'),
                                       linedate.strftime('%Y-%m-%d')))
    else:
        archive_fp.write(line)
    archived_last = True


if __name__ == '__main__':
    try:
        REMIND_DIR = sys.argv[1]
        remind_filename = os.path.expanduser(os.path.join(REMIND_DIR,
                                                          "remind.txt"))
        save_name = os.path.expanduser(os.path.join(REMIND_DIR,
                                                    "remind.txt.new"))
        archive_name = os.path.expanduser(os.path.join(REMIND_DIR,
                                                       "archived.txt"))
        assert(os.path.exists(remind_filename))
    except:
        print("Usage: %s REMIND_DIR" % os.path.basename(sys.argv[0]))
        print("REMIND_DIR should contain a file named remind.txt")
        sys.exit(1)

    with open(remind_filename) as fp:
        seen_start = False
        for line in fp:
            sline = line.strip()

            # First check for the start and end comments
            if sline.startswith('#'):
                if seen_start:
                    if "End Current" in line:
                        seen_start = False
                        if DEBUG:
                            print("***** ENDING ***", file=sys.stderr)
                        save_line(line)
                        continue
                else:
                    if "Current" in line:
                        seen_start = True
                        if DEBUG:
                            print("***** STARTING ***", file=sys.stderr)
                        save_line(line)
                        continue

            if not seen_start:
                save_line(line)
                continue

            # Blank lines and comments should go to the file written last
            if not sline or sline.startswith("#"):
                if archived_last and seen_start:
                    archive_line(line)
                else:
                    save_line(line)
                continue

            # We think it's a date line. So check the date via keep_line().
            keep, linedate = keep_line(sline)
            if keep:
                save_line(line)
            else:
                archive_line(line, linedate)

    if save_fp:
        save_fp.close()
        os.rename(remind_filename, remind_filename + ".bak")
        os.rename(save_name, remind_filename)
        print("Saved new", remind_filename)

    if archive_fp:
        archive_fp.close()
