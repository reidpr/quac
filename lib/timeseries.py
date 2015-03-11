# Copyright © Los Alamos National Security, LLC, and others.

'''Functionality for reading and manipulating time series vectors.

   We refer to "shards" in the namespace/name dimension and "fragments" in the
   time dimenstion. That is, two time series with different namespaces and/or
   names might fall in different shards, and different elements in the same
   time series might fall in different fragments, but all elements in the same
   time series will be in the same shard, and all elements for the same time
   will be in the same fragment. Fragments are tagged with arbitrary,
   contiguously ordered strings and shards are tagged with contiguous integers
   from 0 to a maximum specified at open time.

   Currently, time series must be hourly (i.e., one element per hour),
   start/end on month boundaries, and have fragments equal to calendar months.
   I have attempted to make the API extensible to remove this limitation
   without disrupting existing code.'''

# FIXME to document
#
# - namespace cannot contain space character
# - when to create indexes
# - update docs for installing apsw
#   - installing at system level invisible in virtualenv)
#   - http://rogerbinns.github.io/apsw/download.html#easy-install-pip-pypi
#   - unzip apsw-3.8.8.2-r1.zip
#   - cd apsw-3.8.8.2-r1
#   - python setup.py fetch --all build --enable-all-extensions install test
#   - --missing-checksum-ok after --all
#   - tests take a while (5-10 minutes), omit if you want to live dangerously; but you can import the module and keep going while the tests run
# - document reason for no setting complete vector

import datetime
import enum
import os
import os.path
import sys

import apsw
import numpy as np

import hash_
import testable
import time_
import u

l = u.l
u.logging_init('test', verbose_=True)
l.debug('')


# Storage schema version
SCHEMA_VERSION = 1

# If a time series fragment is less than or equal to this, then the vector is
# stored compressed. The reasoning is to avoid wasting space on shards that
# are almost all zeros. In principle this can be changed on a case by cases
# basis, but the API does not currently support that.
#
# The value here is a random guess and is not supported by evidence.
FRAGMENT_TOTAL_ZMAX = 2

# Data types for different vectors. We use floating-point types, even though
# they represent counts, for convenience in processing and the NaN value.
TIMESERIES_TYPE = np.float32
NAMESPACE_TOTAL_TYPE = np.float64

class Fragment_Source(enum.Enum):
   'Where did a fragment come from? True values indicate from storage.'
   usv = 0; unsaved = 0       # created from scratch
   uco = 1; uncompressed = 1  # retrieved without compression from the database
   cps = 2; compressed = 2    # decompressed from the database


class Dataset(object):

   __slots__ = ('filename',
                'hashmod')

   def __init__(self, filename, hashmod):
      self.filename = filename
      self.hashmod = hashmod

   def dump(self):
      for sid in range(self.hashmod):
         for ts in self.fetch_all():
            print(ts)

   def fetch_all(self):
      return list()  # FIXME

   def open_month(self, month, writeable=False):
      if (month.day != 1):
         raise ValueError('month must have day=1, not %d' % month.day)
      if (hasattr(month, 'hour') and (   month.hour != 0
                                      or month.minute != 0
                                      or month.second != 0
                                      or month.microsecond != 0)):
         raise ValueError('month must have all sub-day attributes equal to zero')
      f = Fragment_Group(self.filename, time_.iso8601_date(month),
                         time_.hours_in_month(month))
      f.open(writeable)
      return f

# fetch(namespace, name) - error if nonexistent
# fetch_all(shard_id)
# fragment_tags_all()


class Fragment_Group(object):

   __slots__ = ('curs',
                'db',
                'filename',
                'length',
                'metadata',
                'tag',
                'writeable')

   def __init__(self, filename, tag, length):
      self.filename = '%s/%s.db' % (filename, tag)
      self.tag = tag
      self.length = length
      self.metadata = { 'schema_version': SCHEMA_VERSION,
                        'fragment_total_zmax': FRAGMENT_TOTAL_ZMAX,
                        'timeseries_type': str(TIMESERIES_TYPE),
                        'namespace_total_type': str(NAMESPACE_TOTAL_TYPE),
                        'hashmod': 'FIXME',  # should be from Dataset
                        'length': self.length }

   def close(self):
      self.db.close()
      self.writeable = None

   def open(self, writeable):
      l.debug('opening %s, writeable=%s' % (self.filename, writeable))
      self.connect(writeable)
      self.initialize_db()
      self.validate_db()

   def connect(self, writeable):
      self.writeable = writeable
      if (writeable):
         flags = apsw.SQLITE_OPEN_READWRITE | apsw.SQLITE_OPEN_CREATE
         os.makedirs(os.path.dirname(self.filename), exist_ok=True)
      else:
         flags = apsw.SQLITE_OPEN_READONLY
      self.db = apsw.Connection(self.filename, flags=flags)
      self.curs = self.db.cursor()

   def initialize_db(self):
      if (not self.writeable):
         l.debug('not writeable, skipping init')
         return
      # FIXME - PRAGMAs
      if (next(self.x("""SELECT COUNT(*)
                         FROM sqlite_master
                         WHERE type='table' AND name='metadata'"""))[0] != 0):
         l.debug('metadata table exists, skipping init')
         return
      l.debug('initializing')
      self.curs.execute("""CREATE TABLE metadata (
                             key    TEXT NOT NULL PRIMARY KEY,
                             value  TEXT NOT NULL
                           )""")
      self.curs.executemany("INSERT INTO metadata VALUES (?, ?)",
                            self.metadata.items())

   def validate_db(self):
      db_meta = dict(self.curs.execute('SELECT key, value FROM metadata'))
      for (k, v) in self.metadata.items():
         if (str(v) != db_meta[k]):
            raise ValueError('Metadata mismatch at key %s: expected %s, found %s'
                             % (k, v, db_meta[k]))
      if (set(db_meta.keys()) != set(self.metadata.keys())):
         raise ValueError('Metadata mismatch: key sets differ')
      l.debug('validated %d metadata items' % len(self.metadata))

   def x(self, sql, bindings=None):
      return self.curs.execute(sql, bindings)

# compact(minimum)
# create_fragment(namespace, name)
# fetch_fragment(namespace, name)
# fetch_or_create_fragment(namespace, name)
# begin()
# commit()
# close()


class Fragment(object):

   __slots__ = ('data',      # time series vector fragment itself
                'namespace',
                'name',
                'start',     # timestamp of fragment start
                'source',    # where the fragment came from
                'total')     # total of data (updated automatically on save)

   def __str__(self):
      pass

   def save(self):
      pass


testable.register('''

# Tests not implemented
#
# - DB does not validate
#   - missing metadata or data tables
#   - table columns do not match
#   - wrong number of data tables (too few, too many)
#   - metadata does not match (items differ, different number of items)
# - timing of create_indexes()
# - duplicate namespace/name pair

>>> import pytz
>>> tmp = os.environ['TMPDIR']
>>> january = time_.iso8601_parse('2015-01-01')
>>> february = time_.iso8601_parse('2015-02-01')
>>> january_nonutc = datetime.datetime(2015, 1, 1, tzinfo=pytz.timezone('GMT'))
>>> mid_january1 = time_.iso8601_parse('2015-01-01 00:00:01')
>>> mid_january2 = time_.iso8601_parse('2015-01-02')

# create some data over 2 months
#
#   ns     name    description
#   -----  ----    -----------
#
#   aboth  abov11  above threshold in both months
#   bboth  abov00  below threshold in both months
#   full   abov11  above threshold in both months
#   full   abov01  above threshold in second month only
#   full   abov10  above threshold in first month only
#   full   abov00  below threshold in both months

# Create time series dataset
>>> d = Dataset(tmp + '/foo', 4)

# Try to open some bogus months
>>> jan = d.open_month(january_nonutc, writeable=True)
Traceback (most recent call last):
  ...
ValueError: time zone must be UTC
>>> jan = d.open_month(mid_january1, writeable=True)
Traceback (most recent call last):
  ...
ValueError: month must have all sub-day attributes equal to zero
>>> jan = d.open_month(mid_january2, writeable=True)
Traceback (most recent call last):
  ...
ValueError: month must have day=1, not 2

# Really open; should be empty so far
>>> jan = d.open_month(january, writeable=True)
>>> feb = d.open_month(february, writeable=True)
>>> d.dump()

# Add first time series
#>>> a.begin()
#>>> a = jan.create('aboth', 'abov11')
#>>> a.data[0] = 99.0
#>>> a.save()
#>>> a.commit()

# Add remaining time series

# Compact

# create time series that would be compressed
# update time series
#   uncompressed -> uncompressed
#   uncompressed -> compressed
#   compressed -> compressed
#   compressed -> uncompressed
# fetch
#   existent
#   nonexistent
# fetch_or_create
#   existent
#   nonexistent
# create already existing fragment fails at save time
# test commit visibility to readers
# fetch nonexistent fragment
# auto-prune save()
# close and re-open

''')
