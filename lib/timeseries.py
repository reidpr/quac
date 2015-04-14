# Copyright © Los Alamos National Security, LLC, and others.

'''
Functionality for reading and manipulating time series vectors.

We refer to "shards" in the name dimension and "fragments" in the time
dimension. That is, two time series with different names might fall in
different shards, and different elements in the same time series might fall in
different fragments, but all elements in the same time series will be in the
same shard, and all elements for the same time will be in the same fragment.
Fragments are tagged with arbitrary, contiguously ordered strings and shards
are tagged with contiguous integers from 0 to a maximum specified at open
time.

Currently, time series must be hourly (i.e., one element per hour), start/end
on month boundaries, and have fragments equal to calendar months. I have
attempted to make the API extensible to remove this limitation without
disrupting existing code.

For example, consider the following time series:

   name  description
   ----  -----------

   f11   above threshold in both months
   d01   above threshold in second month only, float64
   f10   above threshold in first month only, at compression threshold in 2nd
   f00   below threshold in both months, above compression threshold

Test setup:

   >>> import pytz
   >>> tmp = os.environ['TMPDIR']
   >>> KEEP_THRESHOLD = 20
   >>> january = time_.iso8601_parse('2015-01-01')
   >>> february = time_.iso8601_parse('2015-02-01')

Create read-write and read-only time series datasets with four shards:

   >>> ds = Dataset(tmp + '/foo', 4, writeable=True)
   >>> ds2 = Dataset(tmp + '/foo', 4)

Open January:

   >>> ds.dump()
   >>> jan = ds.open_month(january)
   >>> ds.dump()
   fragment 2015-01-01
   shard 0
   shard 1
   shard 2
   shard 3

Add the first time series fragment:

   >>> jan.begin()
   >>> a = jan.create('f11')
   >>> a
   f11 nf 0.0 []
   >>> a.data[0] = 11
   >>> a
   f11 nf 0.0 [(0, 11.0)]
   >>> a.data[2] = 22.0
   >>> a
   f11 nf 0.0 [(0, 11.0), (2, 22.0)]
   >>> a.save()
   >>> jan.commit()
   >>> ds.dump()
   fragment 2015-01-01
   shard 0
   shard 1
   shard 2
   shard 3
     f11 uf 33.0 [(0, 11.0), (2, 22.0)]

Try some fetching:

   >>> jan.fetch('f11')
   f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   >>> jan.fetch('nonexistent')
   Traceback (most recent call last):
     ...
   db.Not_Enough_Rows_Error: no such row
   >>> jan.fetch_or_create('f11')
   f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   >>> jan.fetch_or_create('nonexistent')
   nonexistent nf 0.0 []

Add the rest of uf11:

   >>> feb = ds.open_month(february)
   >>> feb.begin()
   >>> a = feb.create('f11')
   >>> a.data[671] = 44
   >>> a.save()
   >>> feb.commit()
   >>> ds.dump()
   fragment 2015-01-01
   shard 0
   shard 1
   shard 2
   shard 3
     f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   fragment 2015-02-01
   shard 0
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 [(671, 44.0)]

Add remaining time series:

   >>> jan.begin()
   >>> b = jan.create('d01', dtype=np.float64)
   >>> b.data[0] = 1
   >>> b.save()
   >>> c = jan.create('f10')
   >>> c.data[0] = 66
   >>> c.save()
   >>> d = jan.create('f00')
   >>> d.data[0] = 0
   >>> d.save()
   >>> jan.commit()
   >>> feb.begin()
   >>> b = feb.create('d01', dtype=np.float64)
   >>> b.data[0] = 55
   >>> b.save()
   >>> c = feb.create('f10')
   >>> c.data[0] = 5
   >>> c.save()
   >>> d = feb.create('f00')
   >>> d.data[0] = 0
   >>> d.save()
   >>> feb.commit()
   >>> ds.dump()
   fragment 2015-01-01
   shard 0
     d01 zd 1.0 [(0, 1.0)]
     f10 uf 66.0 [(0, 66.0)]
   shard 1
     f00 zf 0.0 []
   shard 2
   shard 3
     f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 [(0, 55.0)]
     f10 zf 5.0 [(0, 5.0)]
   shard 1
     f00 zf 0.0 []
   shard 2
   shard 3
     f11 uf 44.0 [(671, 44.0)]

A fragment is compressed if its total is below a threshold:

   >>> feb.begin()
   >>> a = feb.create('foo')
   >>> a
   foo nf 0.0 []
   >>> a.save()  # new to compressed
   >>> a = feb.fetch('foo')
   >>> a
   foo zf 0.0 []
   >>> a.data[0] = 5
   >>> a.save()  # compressed to compressed
   >>> a = feb.fetch('foo')
   >>> a
   foo zf 5.0 [(0, 5.0)]
   >>> a.data[0] = 6
   >>> a.save()  # compressed to uncompressed
   >>> a = feb.fetch('foo')
   >>> a
   foo uf 6.0 [(0, 6.0)]
   >>> a.data[0] = 7
   >>> a.save()  # uncompressed to uncompressed
   >>> a = feb.fetch('foo')
   >>> a
   foo uf 7.0 [(0, 7.0)]
   >>> a.data[0] = 2
   >>> a.data[1] = 3
   >>> a.save()  # uncompressed to compressed
   >>> a = feb.fetch('foo')
   >>> a
   foo zf 5.0 [(0, 2.0), (1, 3.0)]
   >>> feb.delete('foo')
   >>> feb.commit()

Duplicate fragments are rejected:

   >>> jan.begin()
   >>> a = jan.create('foo')
   >>> b = jan.create('foo')
   >>> a.save()
   >>> b.save()
   Traceback (most recent call last):
     ...
   apsw.ConstraintError: ConstraintError: UNIQUE constraint failed: ...
   >>> jan.db.rollback()

Calling prune() will remove all fragments with a total below a certain
threshold, as well as compact the database.

   >>> jan.prune(KEEP_THRESHOLD)
   >>> feb.prune(KEEP_THRESHOLD)
   >>> ds.dump()
   fragment 2015-01-01
   shard 0
     f10 uf 66.0 [(0, 66.0)]
   shard 1
   shard 2
   shard 3
     f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 [(0, 55.0)]
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 [(671, 44.0)]

You can also prune at save time, in which case pruned data will never touch
the database:

   >>> jan.begin()
   >>> a = jan.create('pruneme')
   >>> a.save(ignore=KEEP_THRESHOLD)
   >>> a = jan.create('keepme')
   >>> a.data[0] = 77
   >>> a.save(ignore=KEEP_THRESHOLD)
   >>> jan.commit()
   >>> ds.dump()
   fragment 2015-01-01
   shard 0
     f10 uf 66.0 [(0, 66.0)]
   shard 1
   shard 2
     keepme uf 77.0 [(0, 77.0)]
   shard 3
     f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 [(0, 55.0)]
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 [(671, 44.0)]

Note, however, that pruning during save time can leave erroneous data if the
fragment already exists.

   >>> jan.begin()
   >>> a = jan.fetch('f10')
   >>> a.data[0] = 1                  # change will be lost
   >>> a                              # total not updated yet
   f10 uf 66.0 [(0, 1.0)]
   >>> a.save(ignore=KEEP_THRESHOLD)
   >>> jan.commit()
   >>> ds.dump()                      # note old value of f10
   fragment 2015-01-01
   shard 0
     f10 uf 66.0 [(0, 66.0)]
   shard 1
   shard 2
     keepme uf 77.0 [(0, 77.0)]
   shard 3
     f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 [(0, 55.0)]
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 [(671, 44.0)]

Uncommitted changes are not visible to simultaneous readers:

   >>> jan.begin()
   >>> a = jan.fetch('f10')
   >>> a.data[1] = 88
   >>> a
   f10 uf 66.0 [(0, 66.0), (1, 88.0)]
   >>> a.save()
   >>> ds2.dump()                     # note old value of f10
   fragment 2015-01-01
   shard 0
     f10 uf 66.0 [(0, 66.0)]
   shard 1
   shard 2
     keepme uf 77.0 [(0, 77.0)]
   shard 3
     f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 [(0, 55.0)]
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 [(671, 44.0)]
   >>> jan.commit()
   >>> ds2.dump()                     # f10 now has updated value
   fragment 2015-01-01
   shard 0
     f10 uf 154.0 [(0, 66.0), (1, 88.0)]
   shard 1
   shard 2
     keepme uf 77.0 [(0, 77.0)]
   shard 3
     f11 uf 33.0 [(0, 11.0), (2, 22.0)]
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 [(0, 55.0)]
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 [(671, 44.0)]

Complete time series can be queried. Note that missing fragments are filled
with zeroes, but series where all fragments have been pruned return not found.

   >>> u.fmt_sparsearray(ds.fetch('f11'))
   [(0, 11.0), (2, 22.0), (1415, 44.0)]
   >>> u.fmt_sparsearray(ds.fetch('d01'))
   [(744, 55.0)]
   >>> ds.fetch('f00')
   Traceback (most recent call last):
     ...
   db.Not_Enough_Rows_Error: no non-zero fragments found

One or more shards can be iterated through:

   >>> for ts in ds.fetch_all(0):
   ...    print(ts[0], ts[1].dtype, len(ts[1]), u.fmt_sparsearray(ts[1]))
   d01 float64 1416 [(744, 55.0)]
   f10 float32 1416 [(0, 66.0), (1, 88.0)]
   >>> for ts in ds.fetch_all(3, 1, 0):
   ...    print(ts[0], ts[1].dtype, len(ts[1]), u.fmt_sparsearray(ts[1]))
   f11 float32 1416 [(0, 11.0), (2, 22.0), (1415, 44.0)]
   d01 float64 1416 [(744, 55.0)]
   f10 float32 1416 [(0, 66.0), (1, 88.0)]

Opening bogus months fails:

   >>> january_nonutc = datetime.datetime(2015, 1, 1,
   ...                                    tzinfo=pytz.timezone('GMT'))
   >>> mid_january1 = time_.iso8601_parse('2015-01-01 00:00:01')
   >>> mid_january2 = time_.iso8601_parse('2015-01-02')
   >>> jan = ds.open_month(january_nonutc)
   Traceback (most recent call last):
     ...
   ValueError: time zone must be UTC
   >>> jan = ds.open_month(mid_january1)
   Traceback (most recent call last):
     ...
   ValueError: must have all sub-day attributes equal to zero
   >>> jan = ds.open_month(mid_january2)
   Traceback (most recent call last):
     ...
   ValueError: must have day=1, not 2

Close the datasets:

   >>> ds.close()
   >>> ds2.close()

Tests not implemented:

   - DB does not validate
     - missing metadata or data tables
     - table columns do not match
     - wrong number of data tables (too few, too many)
     - metadata does not match (items differ, different number of items)
   - timing of create_indexes()
   - writing beyond array limits
   - mixed data types in different fragments
   - data less than zero
   - inferring hashmod from existing Dataset
   - non-zero fill (this is tested separately in the script tests)
'''

import datetime
import enum
import glob
import itertools
import heapq
import os
import os.path
import sys
import zlib

import numpy as np

import db
import hash_
import testable
import time_
import u

l = u.l
#u.logging_init('test', verbose_=True)
#l.debug('')


# Storage schema version
SCHEMA_VERSION = 1

# If a time series fragment is less than or equal to this, then the vector is
# stored compressed. The reasoning is to avoid wasting space on shards that
# are almost all zeros. In principle this can be changed on a case by cases
# basis, but the API does not currently support that.
#
# The value here is a random guess and is not supported by evidence.
FRAGMENT_TOTAL_ZMAX = 5

# Compression level, 1-9. Changing this will not affect the readability of
# existing files.
ZLEVEL = 9

# Default data type
TYPE_DEFAULT = np.float32

# Which hash algorithm to use?
HASH = 'fnv1a_32'
hashf = getattr(hash_, HASH)

class Fragment_Source(enum.Enum):
   'Where did a fragment come from?'
   n = 1; NEW = 1           # created from scratch
   u = 2; UNCOMPRESSED = 2  # retrieved without compression from the database
   z = 3; COMPRESSED = 3    # decompressed from the database


class Dataset(object):

   __slots__ = ('filename',
                'groups',
                'hashmod',
                'writeable')

   def __init__(self, filename, hashmod, writeable=False):
      self.filename = filename
      self.hashmod = hashmod
      self.writeable = writeable
      self.groups = dict()

   @property
   def fragment_tag_first(self):
      return next(self.fragment_tags)

   @property
   def fragment_tags(self):
      for g in glob.iglob('%s/*.db' % self.filename):
         yield os.path.split(os.path.splitext(g)[0])[1]

   def assemble(self, fragments):
      fmap = { tag: None for tag in self.fragment_tags }
      fmap.update({ f.group.tag: f for f in fragments })
      for (tag, f) in fmap.items():
         if (f is None):
            fmap[tag] = self.group_get(tag).create(None)
      return np.concatenate([f.data for (tag, f) in sorted(fmap.items())])

   def close(self):
      for g in self.groups.values():
         g.close()

   def dump(self):
      for ft in self.fragment_tags:
         print('fragment %s' % ft)
         fg = self.group_get(ft)
         fg.dump()

   def fetch(self, name):
      fs = list()
      for t in self.fragment_tags:
         fg = self.group_get(t)
         fs.append(fg.fetch_or_create(name))
      if (not any(f.total for f in fs)):
         raise db.Not_Enough_Rows_Error('no non-zero fragments found')
      return self.assemble(fs)

   def fetch_all(self, *shards):
      for sh in shards:
         fgs = [self.group_get(t).fetch_all(sh) for t in self.fragment_tags]
         for (name, fragments) in itertools.groupby(heapq.merge(*fgs),
                                                    lambda x: x.name):
            yield (name, self.assemble(fragments))

   def open_month(self, month):
      if (month.day != 1):
         raise ValueError('must have day=1, not %d' % month.day)
      if (hasattr(month, 'hour') and (   month.hour != 0
                                      or month.minute != 0
                                      or month.second != 0
                                      or month.microsecond != 0)):
         raise ValueError('must have all sub-day attributes equal to zero')
      return self.group_get(time_.iso8601_date(month),
                            time_.hours_in_month(month))

   def put(self, name, tag_first, ts):
      assert False, 'unimplemented'

   def group_get(self, tag, length=None):
      if (not tag in self.groups):
         fg = Fragment_Group(self, self.filename, tag, length)
         fg.open(self.writeable)
         self.groups[tag] = fg
      return self.groups[tag]

   def shard(self, name):
      return hashf(name) % self.hashmod


class Fragment_Group(object):

   __slots__ = ('curs',
                'dataset',
                'db',
                'filename',
                'length',
                'metadata',
                'tag',
                'writeable')

   def __init__(self, dataset, filename, tag, length=None):
      self.dataset = dataset
      self.filename = '%s/%s.db' % (filename, tag)
      self.tag = tag
      self.length = length
      self.metadata = { 'fragment_total_zmax': FRAGMENT_TOTAL_ZMAX,
                        'hash': HASH,
                        'hashmod': self.dataset.hashmod,
                        'length': self.length,
                        'schema_version': SCHEMA_VERSION }

   def begin(self):
      self.db.begin()

   def close(self):
      self.db.close()
      self.writeable = None

   def commit(self):
      self.db.commit()

   def connect(self, writeable):
      self.writeable = writeable
      if (writeable):
         os.makedirs(os.path.dirname(self.filename), exist_ok=True)
      self.db = db.SQLite(self.filename, writeable)

   def create(self, name, dtype=TYPE_DEFAULT, fill=None):
      'Create and return a fragment initialized to zero or fill.'
      data = np.zeros(self.length, dtype=dtype)
      if (fill is not None):
         data[:] = fill
      return Fragment(self, name, data, Fragment_Source.NEW)

   def delete(self, name):
      self.db.sql(("DELETE FROM data%d WHERE name=?"
                   % self.dataset.shard(name)), (name,))

   def deserialize(self, name, dtype, total, data):
      if (total <= FRAGMENT_TOTAL_ZMAX):
         #print(name, dtype, total, data, file=sys.stderr)
         data = zlib.decompress(data)
         source = Fragment_Source.COMPRESSED
      else:
         source = Fragment_Source.UNCOMPRESSED
      ar = np.frombuffer(data, dtype=dtype)
      f = Fragment(self, name, ar, source)
      f.total = total
      # np.frombuffer() sets writeable=False by default. I am guessing that it
      # is safe to set it True instead, because we can do so without barfing,
      # but one should be cautious. If this causes problems, we could change
      # the API to make all fetched fragments read-only unless otherwise
      # specified, and make a copy if writing is desired.
      f.data.flags.writeable = True
      return f

   def dump(self):
      for shard in range(self.dataset.hashmod):
         print('shard %d' % shard)
         for f in self.fetch_all(shard):
            print(' ', f)

   def empty_p(self):
      sql = ("SELECT SUM(a) FROM (%s LIMIT 1)"
             % " UNION ".join("SELECT 1 AS a FROM data%d" % i
                              for i in range(self.dataset.hashmod)))
      return not self.db.get_one(sql)[0]

   def fetch(self, name):
      (dtype, total, data) \
         = self.db.get_one("""SELECT dtype, total, data FROM data%d
                               WHERE name=?""" % self.dataset.shard(name),
                           (name,))
      return self.deserialize(name, dtype, total, data)

   def fetch_all(self, shard):
      for i in self.db.get("""SELECT name, dtype, total, data
                              FROM data%d
                              ORDER BY name""" % shard):
         yield self.deserialize(*i)

   def fetch_or_create(self, name, dtype=TYPE_DEFAULT, fill=None):
      '''dtype is only used on create; if fetch is successful, the fragment is
         returned unchanged.'''
      try:
         return self.fetch(name)
      except db.Not_Enough_Rows_Error:
         return self.create(name, dtype, fill)

   def initialize_db(self):
      if (self.db.exists('sqlite_master', "type='table' AND name='metadata'")):
         l.debug('found metadata table, assuming already initalized')
         if (self.length is None):
            self.length = int(self.db.get_one("""SELECT value FROM metadata
                                                 WHERE key = 'length'""")[0])
            self.metadata['length'] = self.length
      else:
         if (not self.writeable):
            raise db.Invalid_DB_Error('cannot initalize in read-only mode')
         l.debug('initializing')
         assert (self.length is not None)
         self.db.sql("""PRAGMA encoding='UTF-8';
                        PRAGMA page_size = 65536; """)
         self.db.begin()
         self.db.sql("""CREATE TABLE metadata (
                          key    TEXT NOT NULL PRIMARY KEY,
                          value  TEXT NOT NULL )""")
         self.db.sql_many("INSERT INTO metadata VALUES (?, ?)",
                          self.metadata.items())
         for i in range(self.dataset.hashmod):
            self.db.sql("""CREATE TABLE data%d (
                             name       TEXT NOT NULL PRIMARY KEY,
                             dtype      TEXT NOT NULL,
                             total      REAL NOT NULL,
                             data       BLOB NOT NULL)
                           WITHOUT ROWID""" % i)
         self.db.commit()

   def open(self, writeable):
      l.debug('opening %s, writeable=%s' % (self.filename, writeable))
      self.connect(writeable)
      # We use journal_mode = PERSIST to avoid metadata operations and
      # re-allocation, which can be expensive on parallel filesystems.
      self.db.sql("""PRAGMA cache_size = -1048576;
                     PRAGMA synchronous = OFF; """)
      self.initialize_db()
      self.validate_db()

   def prune(self, keep_thr):
      l.debug('pruning with threshold = %d' % keep_thr)
      for si in range(self.dataset.hashmod):
         # I originally planned to do this with CREATE TABLE AS SELECT into a
         # temporary table, to put everything in order, but one can't do that
         # and retain the WITHOUT ROWID property.
         self.db.sql("DELETE FROM data%d WHERE total < ?" % si, (keep_thr,))
      l.debug('deleted pruneable rows')
      self.db.sql("VACUUM");
      page_size = self.db.get_one("PRAGMA page_size")[0]
      free_ct = self.db.get_one("PRAGMA freelist_count")[0]
      total_ct = self.db.get_one("PRAGMA page_count")[0]
      l.debug('vacuumed: %s used; %d total, %d free pages'
              % (u.fmt_bytes(page_size * total_ct), total_ct, free_ct))

   def validate_db(self):
      db_meta = dict(self.db.get('SELECT key, value FROM metadata'))
      for (k, v) in self.metadata.items():
         if (str(v) != db_meta[k]):
            raise db.Invalid_DB_Error(
               'Metadata mismatch at key %s: expected %s, found %s'
               % (k, v, db_meta[k]))
      if (set(db_meta.keys()) != set(self.metadata.keys())):
         raise db.Invalid_DB_Error('Metadata mismatch: key sets differ')
      l.debug('validated %d metadata items' % len(self.metadata))


class Fragment(object):

   __slots__ = ('data',      # time series vector fragment itself
                'group',
                'name',
                'source',    # where the fragment came from
                'total')     # total of data (not updated when data changes)

   def __init__(self, group, name, data, source):
      self.group = group
      self.name = name
      self.data = data
      self.source = source
      self.total = 0.0

   # Compare on the name attribute, to faciliate sorting. Note that equality
   # is not defined, since it seems odd to have two fragments compare equal
   # merely because they share a name.
   def __lt__(self, other):
      return self.name < other.name

   @property
   def shard(self):
      return self.group.dataset.shard(self.name)

   def __repr__(self):
      'Mostly for testing; output is inefficient for non-sparse fragments.'
      return '%s %s%s %s %s' % (self.name, self.source.name,
                                self.data.dtype.char, self.total,
                                u.fmt_sparsearray(self.data))

   def save(self, ignore=-1):
      self.total_update()
      if (self.total < ignore):
         return False
      if (self.total <= FRAGMENT_TOTAL_ZMAX):
         data = zlib.compress(self.data.data, ZLEVEL)
      else:
         data = self.data.data
      if (self.source == Fragment_Source.NEW):
         self.group.db.sql("""INSERT INTO data%d (name, dtype, total, data)
                              VALUES (?, ?, ?, ?)""" % self.shard,
                           (self.name, self.data.dtype.char, self.total, data))
      else:
         self.group.db.sql("""UPDATE data%d
                              SET dtype=?, total=?, data=?
                              WHERE name=?""" % self.shard,
                           (self.data.dtype.char, self.total, data, self.name))
      return True

   def total_update(self):
      # np.sum() returns a NumPy data type, which confuses SQLite somehow.
      # Therefore, use a plain Python float. Also np.sum() is about 30 times
      # faster than Python sum() on a 1000-element array.
      self.total = float(abs(self.data).sum())


testable.register()
