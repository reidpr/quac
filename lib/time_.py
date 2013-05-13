# Various time stuff.
#
# Why this isn't simply a part of the standard library, I have no idea. IMO
# there is a special place in hell for the people who designed Python time
# handling -- why are simple things so hard?


from datetime import tzinfo, timedelta, datetime
import pytz
import re
import time as _time

from dateutil import rrule
import isodate

import testable


# matches ISO 8601 datetimes with a space separator
ISO8601_SPACE_SEP = re.compile(r'(\d\d\d\d-\d\d-\d\d)( )(.*)$')

# the oldest datetime
datetime_min = datetime(1, 1, 1)


def as_utc(dt):
   '''Convert an aware datetime with an arbitrary time zone into the
      equivalent UTC datetime.'''
   return dt.astimezone(pytz.utc)

def dateseq_str(start, end):
   '''Return a sequence of date strings from start to end (in ISO 8601
      format), inclusive. e.g.:

      >>> dateseq_str('2013-03-25', '2013-03-28')
      ['2013-03-25', '2013-03-26', '2013-03-27', '2013-03-28']'''
   start = iso8601_parse(start)
   end = iso8601_parse(end)
   return [d.strftime('%Y-%m-%d') for d in dateseq(start, end)]

def dateseq(start, end):
   return rrule.rrule(rrule.DAILY, dtstart=start, until=end)

def days_f(td):
   '''Return the fractional number of days in timedelta td. E.g.:

      >>> td = timedelta(days=2.5)
      >>> td.days
      2
      >>> days_f(td)
      2.5'''
   return td.total_seconds() / timedelta(days=1).total_seconds()

def ddfs_parse(text):
   '''Parse the time string as reported by DDFS. e.g.:

      >>> ddfs_parse('2013/03/20 15:58:22')
      datetime.datetime(2013, 3, 20, 15, 58, 22)'''
   return datetime.strptime(text, '%Y/%m/%d %H:%M:%S')

def localify(dt):
   'Convert a native datetime object into aware one in local time.'
   return dt.replace(tzinfo=local_tz)

def twitter_timestamp_parse(text):
   'Parse a Twitter timestamp string and return a datetime object.'
   #
   # Previously, we used dateutils.parser.parse() for this, as it's able to
   # deal with time zones and requires no format string. However, (a) it's
   # slow, and (b) all Twitter timestamps seem to be in UTC (i.e., timezone
   # string is a constant "+0000"). Therefore, we use this technique, which is
   # approximately 5x faster. (If assumption (b) fails, you'll get a
   # ValueError.)
   return utcify(datetime.strptime(text, '%a %b %d %H:%M:%S +0000 %Y'))

def iso8601utc_parse(text):
   '''Parse a timestamp with seconds in ISO 8601 format, assuming it has a UTC
      offset. Either space or T can be used as a separator. For example:

      >>> iso8601utc_parse('2012-10-26T09:33:00+00:00')
      datetime.datetime(2012, 10, 26, 9, 33, tzinfo=<UTC>)
      >>> iso8601utc_parse('2012-10-26 09:33:00+00:00')
      datetime.datetime(2012, 10, 26, 9, 33, tzinfo=<UTC>)'''
   # This function is here because it's faster than relying on isodate, though
   # I haven't actually tested that.
   text = ISO8601_SPACE_SEP.sub(r'\1T\3', text)
   return utcify(datetime.strptime(text, '%Y-%m-%dT%H:%M:%S+00:00'))

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

def utcify(dt):
   'Convert a native datetime object into aware one in UTC.'
   return dt.replace(tzinfo=pytz.utc)


### The following are copied from the examples at
### http://docs.python.org/library/datetime.html#tzinfo-objects

ZERO = timedelta(0)

# A class capturing the platform's idea of local time.

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

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
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

local_tz = LocalTimezone()


testable.register('')
