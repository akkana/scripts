#! /usr/bin/env python

# Does a day of week or month fall between two dates?
# Copyright 2012 by Akkana Peck: share and enjoy under the GPLv2 or later.

import time

def falls_between(when, time1, time2) :
    """Does a given day-of-week or day-of-month fall between
       the two given times? It is presumed that time1 <= time2.
       If when == "Tue", did we cross a tuesday getting from time1 to time2?
       If when == 15, did we cross the 15th of a month?
       If when == none, return True.
       If when matches time2, return True.
    """

    if not when or type(when) is str and len(when) <= 0 :
        return True

    # We need both times both in seconds since epoch and in struct_time:
    def both_time_types(t) :
        """Given a time that might be either seconds since epoch or struct_time,
           return a tuple of (seconds, struct_time).
        """
        if type(t) is time.struct_time :
            return time.mktime(t), t
        elif type(t) is int or type(t) is float :
            return t, time.localtime(t)
        else : raise ValueError("%s not int or struct_time" % str(t))

    (t1, st1) = both_time_types(time1)
    (t2, st2) = both_time_types(time2)

    daysdiff = (t2 - t1) / 60. / 60. / 24.

    # Is it a day of the month?
    try :
        day_of_month = int(when)

        # It is a day of the month! How many days in between the two dates?
        if daysdiff > 31 :
            return True

        # Now we know the two dates differ by less than a month.
        # Are time1 and time2 both in the same month? Then it's easy.
        if st1.tm_mon == st2.tm_mon :
            return st1.tm_mday <= day_of_month and st2.tm_mday >= day_of_month

        # Else time1 is the month prior to time2, so:
        return st1.tm_mday < day_of_month or day_of_month <= st2.tm_mday

    except ValueError :  # Not an integer, probably a string.
        pass

    if type(when) is not str :
        raise ValueError("%s must be a string or integer" % when)

    # Okay, not a day of the month. Is it a day of the week?
    # We have to start with Monday because struct_time.tm_wday does.
    weekdays = [ 'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su' ]
    if len(when) < 2 :
        raise ValueError("%s too short: days must have at least 2 chars" % when)

    when = when[0:2].lower()
    if when not in weekdays :
        raise ValueError("%s is a string but not a day" % when)

    # Whew -- we know it's a day of the week.

    # Has more than a week passed? Then it encompasses all weekdays.
    if daysdiff > 7 :
        return True

    day_of_week = weekdays.index(when)
    return  (st2.tm_wday - day_of_week) % 7 < daysdiff

# Unit tests:
if __name__ == "__main__" :
    #
    # Day of week tests:
    #
    assert falls_between('Mon',
                         time.strptime('Sun Aug 12 16:00:00 2012'),
                         time.strptime('Wed Aug 15 16:00:00 2012'))
    assert falls_between('we',
                         time.strptime('Sun Aug 12 16:00:00 2012'),
                         time.strptime('Wed Aug 15 16:00:00 2012'))
    assert falls_between('monday',
                         time.strptime('Wed Aug 01 16:00:00 2012'),
                         time.strptime('Wed Aug 15 16:00:00 2012'))
    assert falls_between('Mon',
                         time.strptime('Fri Aug 12 16:00:00 2011'),
                         time.strptime('Sun Aug 12 16:00:00 2012'))
    assert not falls_between('Tuesday',
                             time.strptime('Wed Aug 01 16:00:00 2012'),
                             time.strptime('Sat Aug 04 16:00:00 2012'))
    assert not falls_between('fri',
                             time.strptime('Mon Aug 06 16:00:00 2012'),
                             time.strptime('Thu Aug 09 16:00:00 2012'))

    #
    # Day of month tests:
    #
    assert falls_between(15,
                         time.strptime('Sun Aug 12 16:00:00 2012'),
                         time.strptime('Wed Aug 15 16:00:00 2012'))
    assert falls_between(13,
                         time.strptime('Sun Aug 12 16:00:00 2012'),
                         time.strptime('Wed Aug 15 16:00:00 2012'))
    assert falls_between(13,
                         time.strptime('Sun Jul 22 16:00:00 2012'),
                         time.strptime('Wed Aug 15 16:00:00 2012'))
    assert falls_between(28,
                         time.strptime('Sun Jul 22 16:00:00 2012'),
                         time.strptime('Wed Aug 15 16:00:00 2012'))
    assert not falls_between(20,
                         time.strptime('Sun Jul 22 16:00:00 2012'),
                         time.strptime('Wed Aug 15 16:00:00 2012'))
    assert not falls_between(17,
                             time.strptime('Sun Aug 12 16:00:00 2012'),
                             time.strptime('Wed Aug 15 16:00:00 2012'))
    assert not falls_between(17,
                             time.strptime('Tue Aug 07 16:00:00 2012'),
                             time.strptime('Wed Aug 15 16:00:00 2012'))

    #
    # Make sure ints and floats both work:
    #
    assert falls_between(15,
                         time.strptime('Sun Aug 12 16:00:00 2012'),
                         1345074924)
    assert falls_between(15,
                         time.strptime('Sun Aug 12 16:00:00 2012'),
                         1345074924.2)
    assert not falls_between(17,
                             time.strptime('Tue Aug 07 16:00:00 2012'),
                             1345074924)
    assert not falls_between(17,
                             time.strptime('Tue Aug 07 16:00:00 2012'),
                             1345074924.53)

    print("All tests passed!")
