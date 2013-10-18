'Handy stuff for Wikimedia and Wikipedia data.'

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

import datetime
import re

import testable
import time_


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
