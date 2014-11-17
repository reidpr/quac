'Handy stuff for Wikimedia and Wikipedia data.'

# Copyright (c) Los Alamos National Security, LLC, and others.

import datetime
import re

import testable
import time_


def hour_bizarro(x):
   '''Convert x into an hour number; it can be a filename or a metadata date
      thingy. In the latter case, both the minimum and maximum available hours
      are returned in a tuple. For example:

      >>> hour_bizarro('2013/2013-10/pagecounts-20131016-090001.gz')
      17643776
      >>> a = (datetime.date(2009, 9, 10),
      ...      {'hours': {2: 9058752, 3: 8307681, 4: 7311189, 5: 6341115},
      ...       'total': 49270827})
      >>> hour_bizarro(a)
      (17607842, 17607845)

      (Yes, this is a strange, very specific function with a weird interface.
      It's what I need, though. It really belongs in wp-hashfiles, but that
      has no tests.)'''
   if (isinstance(x, str)):
      dt = timestamp_parse(x)
      return dt.toordinal() * 24 + dt.hour
   else:
      do = x[0].toordinal() * 24
      return (do + min(x[1]['hours'].keys()),
              do + max(x[1]['hours'].keys()))


def timestamp_parse(text):
   '''Parse the timestamp embedded in pagecount and projectcount files. A
      quirk is that the stamp marks the *end* of the data collection period;
      as we want the beginning, we subtract an hour to compensate (e-mail from
      ariel@wikimedia.org, 2013-09-11). Also, these files are nominally
      created on the hour, but often they are a few seconds later; we ignore
      this to keep consistent intervals. Finally, extra cruft before and after
      the timestamp is permitted. For example:

      >>> timestamp_parse('2013/2013-10/pagecounts-20131016-090001.gz')
      datetime.datetime(2013, 10, 16, 8, 0, tzinfo=<UTC>)
      >>> timestamp_parse('pagecounts-20120101-000000.gz')
      datetime.datetime(2011, 12, 31, 23, 0, tzinfo=<UTC>)
      >>> timestamp_parse('2013/2013-10/projectcounts-20131016-09000')
      Traceback (most recent call last):
        ...
      ValueError: no timestamp found
      >>> timestamp_parse('2013/2013-10/projectcounts-99999999-999999')
      Traceback (most recent call last):
        ...
      ValueError: time data '99999999-999999' does not match format '%Y%m%d-%H%M%S'
'''
   m = re.search(r'(\d{8}-\d{6})(\.gz)?', text)
   if (m is None):
      raise ValueError('no timestamp found')
   t = datetime.datetime.strptime(m.group(1), '%Y%m%d-%H%M%S')
   t = datetime.datetime(t.year, t.month, t.day, t.hour)
   t = time_.utcify(t)
   return (t - datetime.timedelta(hours=1))


testable.register('')
