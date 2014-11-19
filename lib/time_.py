# Various time stuff.
#
# Why this isn't simply a part of the standard library, I have no idea. IMO
# there is a special place in hell for the people who designed Python time
# handling -- why are simple things so hard?
#
# Copyright (c) Los Alamos National Security, LLC, and others.

import datetime
from pprint import pprint
import pytz
import re
import time

from dateutil import rrule, relativedelta
import isodate

import testable


# matches ISO 8601 datetimes with a space separator
ISO8601_SPACE_SEP = re.compile(r'(\d\d\d\d-\d\d-\d\d)( )(.*)$')

# datetime and time limits
datetime_min = datetime.datetime(datetime.MINYEAR,  1,  1,  0,  0,  0)
datetime_max = datetime.datetime(datetime.MAXYEAR, 12, 31, 23, 59, 59)
date_min = datetime_min.date()
date_max = datetime_max.date()


def as_utc(dt):
   '''Convert an aware datetime with an arbitrary time zone into the
      equivalent UTC datetime.'''
   return dt.astimezone(pytz.utc)

def date_hours(d):
   '''Given a date object, return an iterable of datetime objects, one for
      each hour on that date. For example:

      >>> pprint(list(date_hours(datetime.date(2013, 10, 31))))
      [datetime.datetime(2013, 10, 31, 0, 0),
       datetime.datetime(2013, 10, 31, 1, 0),
       datetime.datetime(2013, 10, 31, 2, 0),
       ...
       datetime.datetime(2013, 10, 31, 23, 0)]'''
   for hour in range(24):
      yield datetime.datetime.combine(d, datetime.time(hour))

def dateify(x):
   '''Try to convert x to a date and return the result. E.g.:

      >>> dateify('2013-06-28')
      datetime.date(2013, 6, 28)
      >>> dateify(datetime.date(2013, 6, 28))
      datetime.date(2013, 6, 28)
      >>> dateify(datetime.datetime(2013, 6, 28))
      datetime.date(2013, 6, 28)
      >>> dateify(None)  # returns None
      >>> dateify(1)
      Traceback (most recent call last):
        ...
      ValueError: can't convert 1 to a date
      >>> dateify('2013-06-31')
      Traceback (most recent call last):
        ...
      ValueError: day is out of range for month
      '''
   if (isinstance(x, datetime.datetime)):
      return x.date()
   if (isinstance(x, datetime.date)):
      return x
   if (x is None):
      return x
   if (isinstance(x, str)):
      return iso8601_parse(x).date()
   raise ValueError("can't convert %s to a date" % (str(x)))

def dateseq_str(start, end):
   '''Return a sequence of date strings from start to end (in ISO 8601
      format), inclusive. e.g.:

      >>> dateseq_str('2013-03-25', '2013-03-28')
      ['2013-03-25', '2013-03-26', '2013-03-27', '2013-03-28']'''
   start = iso8601_parse(start)
   end = iso8601_parse(end)
   return [iso8601_date(d) for d in dateseq(start, end)]

def dateseq(start, end):
   '''E.g.:

      >>> pprint(list(dateseq(datetime.date(2013, 3, 25),
      ...                     datetime.date(2013, 3, 28))))
      [datetime.date(2013, 3, 25),
       datetime.date(2013, 3, 26),
       datetime.date(2013, 3, 27),
       datetime.date(2013, 3, 28)]
      >>> pprint(list(dateseq(datetime.datetime(2013, 3, 25, 1, 2, 3),
      ...                     datetime.datetime(2013, 3, 28, 4, 5, 6))))
      [datetime.date(2013, 3, 25),
       datetime.date(2013, 3, 26),
       datetime.date(2013, 3, 27),
       datetime.date(2013, 3, 28)]'''
   return (dt.date()
           for dt in rrule.rrule(rrule.DAILY, dtstart=start, until=end))

def days_f(td):
   '''Return the fractional number of days in timedelta td. E.g.:

      >>> td = datetime.timedelta(days=2.5)
      >>> td.days
      2
      >>> days_f(td)
      2.5'''
   return td.total_seconds() / datetime.timedelta(days=1).total_seconds()

def days_diff(a, b):
   '''a and b are date or datetime objects that are an integer number of days
      apart. Return a - b in days. E.g.:

      >>> from datetime import datetime, date
      >>> days_diff(datetime(2013, 6, 27), datetime(2013, 6, 20))
      7
      >>> days_diff(date(2013, 6, 27), date(2013, 6, 20))
      7
      >>> days_diff(datetime(2013, 6, 27), date(2013, 6, 20))
      7
      >>> days_diff(date(2013, 6, 27), datetime(2013, 6, 20))
      7
      >>> days_diff(date(2013, 6, 20), date(2013, 6, 27))
      -7
      >>> days_diff(date(2013, 6, 20), date(2013, 6, 20))
      0
      >>> days_diff(datetime(2013, 6, 27, 1), datetime(2013, 6, 20))
      Traceback (most recent call last):
        ...
      ValueError: 2013-06-27 01:00:00 and 2013-06-20 00:00:00 day difference is not an integer
      >>> days_diff(datetime(2013, 6, 27, microsecond=1), datetime(2013, 6, 20))
      Traceback (most recent call last):
        ...
      ValueError: 2013-06-27 00:00:00.000001 and 2013-06-20 00:00:00 day difference is not an integer'''
   if (not isinstance(a, datetime.datetime)):
      a = datetime.datetime.combine(a, datetime.time())
   if (not isinstance(b, datetime.datetime)):
      b = datetime.datetime.combine(b, datetime.time())
   diff = a - b
   if (diff.seconds != 0 or diff.microseconds != 0):
      raise ValueError('%s and %s day difference is not an integer' % (a, b))
   return diff.days

def ddfs_parse(text):
   '''Parse the time string as reported by DDFS. e.g.:

      >>> ddfs_parse('2013/03/20 15:58:22')
      datetime.datetime(2013, 3, 20, 15, 58, 22)'''
   return datetime.datetime.strptime(text, '%Y/%m/%d %H:%M:%S')

def hour_offset(dt):
   '''Return the number of hours between the given datetime and the beginning of
      its month. Time zone must be UTC. Minutes, seconds, and microseconds
      must be zero.

        >>> hour_offset(iso8601_parse('2014-09-01 00:00:00'))
        0
        >>> hour_offset(iso8601_parse('2014-09-01 01:00:00'))
        1
        >>> hour_offset(iso8601_parse('2014-09-30 22:00:00'))
        718
        >>> hour_offset(iso8601_parse('2014-09-30 23:00:00'))
        719

      Error conditions:

        >>> hour_offset(iso8601_parse('2014-09-26 09:33:00'))
        Traceback (most recent call last):
           ...
        ValueError: minutes, seconds, and microseconds must be zero
        >>> hour_offset(iso8601_parse('2014-09-26 09:00:33'))
        Traceback (most recent call last):
           ...
        ValueError: minutes, seconds, and microseconds must be zero
        >>> hour_offset(datetime.datetime(2014, 9, 26, 9, 0, 0, 1, pytz.utc))
        Traceback (most recent call last):
           ...
        ValueError: minutes, seconds, and microseconds must be zero
        >>> hour_offset(iso8601_parse('2014-09-26 09:00:00+01:00'))
        Traceback (most recent call last):
           ...
        ValueError: time zone must be UTC'''
   if (dt.tzinfo != pytz.utc):
      raise ValueError('time zone must be UTC')
   if (not (dt.minute == dt.second == dt.microsecond)):
      raise ValueError('minutes, seconds, and microseconds must be zero')
   start = datetime.datetime(dt.year, dt.month, 1, tzinfo=dt.tzinfo)
   delta = relativedelta.relativedelta(dt, start)
   return int(round(delta.days * 24 + delta.hours))

def hours_in_month(dt):
   '''Return the number of hours in the month of the given datetime, which must
      be in UTC.

      A standard, straightforward month of 30 days:

        >>> hours_in_month(iso8601_parse('2014-09-26 09:33:00'))
        720

      Leap year February (2000 was indeed a leap year):

        >>> hours_in_month(iso8601_parse('2000-02-26 09:33:00'))
        696

      Non leap year February:

        >>> hours_in_month(iso8601_parse('2100-02-26 09:33:00'))
        672

      UTC does not have DST (October contains the DST to standard time
      transition in the US):

        >>> hours_in_month(iso8601_parse('2014-10-26 09:33:00'))
        744

      Non-UTC datetime fails:

        >>> hours_in_month(iso8601_parse('2014-10-26 09:33:00+01:00'))
        Traceback (most recent call last):
           ...
        ValueError: time zone must be UTC

      This really should work, since an offset of 0 is UTC by definition, but
      it doesn't because time zone comparison is hard for some reason.

        >>> hours_in_month(iso8601_parse('2014-10-26 09:33:00+00:00'))
        Traceback (most recent call last):
           ...
        ValueError: time zone must be UTC'''

   if (dt.tzinfo != pytz.utc):
      raise ValueError('time zone must be UTC')
   start_inclusive = datetime.datetime(dt.year, dt.month, 1)
   end_exclusive = start_inclusive + relativedelta.relativedelta(months=1)
   delta = end_exclusive - start_inclusive
   return int(round(delta.days * 24 + delta.seconds / 3600))

def iso8601_date(d):
   return d.strftime('%Y-%m-%d')

def iso8601utc_parse(text):
   '''Parse a timestamp with seconds in ISO 8601 format, assuming it has a UTC
      offset. Either space or T can be used as a separator. For example:

      >>> iso8601utc_parse('2012-10-26T09:33:00+00:00')
      datetime.datetime(2012, 10, 26, 9, 33, tzinfo=<UTC>)
      >>> iso8601utc_parse('2012-10-26 09:33:00+00:00')
      datetime.datetime(2012, 10, 26, 9, 33, tzinfo=<UTC>)'''
   # This function is here because I belive it's faster than relying on
   # isodate, though I haven't actually tested that.
   text = ISO8601_SPACE_SEP.sub(r'\1T\3', text)
   return utcify(datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%S+00:00'))

def iso8601_parse(text):
   '''Parse a date or datetime in ISO 8601 format and return a datetime
      object. For datetimes, can handle either "T" or " " as a separator.'''
   # WARNING: ISO dates have no notion of time zone. Thus, if you want a
   # datetime in a time zone other than local time, you must include a time.
   try:
      text = ISO8601_SPACE_SEP.sub(r'\1T\3', text)
      dt = isodate.parse_datetime(text)
   except ValueError:
      # no time specified, assume midnight at beginning of day
      dt = isodate.parse_datetime(text + 'T00:00')
   if (dt.tzinfo is None):
      # make aware, assuming UTC
      dt = utcify(dt)
   return dt

def localify(dt):
   'Convert a native datetime object into aware one in local time.'
   return dt.replace(tzinfo=local_tz)

def nowstr_human():
   '''Return a human-readable string representing the current time, including
      time zone.'''
   return time.strftime('%c %Z')

def twitter_timestamp_parse(text):
   'Parse a Twitter timestamp string and return a datetime object.'
   #
   # Previously, we used dateutils.parser.parse() for this, as it's able to
   # deal with time zones and requires no format string. However, (a) it's
   # slow, and (b) all Twitter timestamps seem to be in UTC (i.e., timezone
   # string is a constant "+0000"). Therefore, we use this technique, which is
   # approximately 5x faster. (If assumption (b) fails, you'll get a
   # ValueError.)
   return utcify(datetime.datetime.strptime(text, '%a %b %d %H:%M:%S +0000 %Y'))

def utcify(dt):
   'Convert a native datetime object into aware one in UTC.'
   return dt.replace(tzinfo=pytz.utc)

def utcnow():
   'Return an "aware" datetime for right now in UTC.'
   # http://stackoverflow.com/a/4530166/396038
   return datetime.datetime.now(pytz.utc)


### The following are copied from the examples at
### http://docs.python.org/library/datetime.html#tzinfo-objects

ZERO = datetime.timedelta(0)

# A class capturing the platform's idea of local time.

STDOFFSET = datetime.timedelta(seconds = -time.timezone)
if time.daylight:
    DSTOFFSET = datetime.timedelta(seconds = -time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(datetime.tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0

local_tz = LocalTimezone()


testable.register('')
