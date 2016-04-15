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

   >>> from pprint import pprint
   >>> import pytz
   >>> tmp = os.environ['TMPDIR']
   >>> KEEP_THRESHOLD = 20
   >>> january = time_.iso8601_parse('2015-01-01')
   >>> february = time_.iso8601_parse('2015-02-01')

Create read-write time series dataset with four shards:

   >>> c = u.configure(None)
   >>> ds = Dataset(tmp + '/foo', 4, writeable=True)

Open January:

   >>> ds.dump()
   length 0 hours
   >>> jan = ds.open_month(january)
   >>> ds.dump()
   length 744 hours
   fragment 2015-01-01
   shard 0
   shard 1
   shard 2
   shard 3

Add the first time series fragment:

   >>> jan.begin()
   >>> a = jan.create('f11')
   >>> a
   f11 nf 0.0 {744z 0n}
   >>> a.data[0] = 11
   >>> a
   f11 nf 0.0 {743z 0n (0, 11.0)}
   >>> a.data[2] = 22.0
   >>> a
   f11 nf 0.0 {742z 0n (0, 11.0), (2, 22.0)}
   >>> a.save()
   True
   >>> jan.commit()
   >>> ds.dump()
   length 744 hours
   fragment 2015-01-01
   shard 0
   shard 1
   shard 2
   shard 3
     f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}

Try some fetching:

   >>> jan.fetch('f11')
   f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}
   >>> jan.fetch('nonexistent')
   Traceback (most recent call last):
     ...
   db.Not_Enough_Rows_Error: no such row
   >>> jan.fetch_or_create('f11')
   f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}
   >>> jan.fetch_or_create('nonexistent')
   nonexistent nf 0.0 {744z 0n}

Add the rest of f11:

   >>> feb = ds.open_month(february)
   >>> feb.begin()
   >>> a = feb.create('f11')
   >>> a.data[671] = 44
   >>> a.save()
   True
   >>> feb.commit()
   >>> ds.dump()
   length 1416 hours
   fragment 2015-01-01
   shard 0
   shard 1
   shard 2
   shard 3
     f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}
   fragment 2015-02-01
   shard 0
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 {671z 0n (671, 44.0)}

Add remaining time series:

   >>> jan.begin()
   >>> b = jan.create('d01', dtype=np.float64)
   >>> b.data[0] = 1
   >>> b.save()
   True
   >>> c = jan.create('f10')
   >>> c.data[0] = 66
   >>> c.save()
   True
   >>> d = jan.create('f00')
   >>> d.data[0] = 0
   >>> d.save()
   True
   >>> jan.commit()
   >>> feb.begin()
   >>> b = feb.create('d01', dtype=np.float64)
   >>> b.data[0] = 55
   >>> b.save()
   True
   >>> c = feb.create('f10')
   >>> c.data[0] = 5
   >>> c.save()
   True
   >>> d = feb.create('f00')
   >>> d.data[0] = 0
   >>> d.save()
   True
   >>> feb.commit()
   >>> ds.dump()
   length 1416 hours
   fragment 2015-01-01
   shard 0
     d01 zd 1.0 {743z 0n (0, 1.0)}
     f10 uf 66.0 {743z 0n (0, 66.0)}
   shard 1
     f00 zf 0.0 {744z 0n}
   shard 2
   shard 3
     f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 {671z 0n (0, 55.0)}
     f10 zf 5.0 {671z 0n (0, 5.0)}
   shard 1
     f00 zf 0.0 {672z 0n}
   shard 2
   shard 3
     f11 uf 44.0 {671z 0n (671, 44.0)}

You can fetch more than one time series at once:

   >>> jan.fetch_many(['f11'])
   [f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}]
   >>> jan.fetch_many(['nonexistent'])
   []
   >>> jan.fetch_many([])
   []
   >>> jan.fetch_many(['f11', 'd01'])
   [d01 zd 1.0 {743z 0n (0, 1.0)}, f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}]
   >>> jan.fetch_many(['f11', 'nonexistent'])
   [f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}]

A fragment is compressed if its total is below a threshold:

   >>> feb.begin()
   >>> a = feb.create('foo')
   >>> a
   foo nf 0.0 {672z 0n}
   >>> a.save()  # new to compressed
   True
   >>> a = feb.fetch('foo')
   >>> a
   foo zf 0.0 {672z 0n}
   >>> a.data[0] = 5
   >>> a.save()  # compressed to compressed
   True
   >>> a = feb.fetch('foo')
   >>> a
   foo zf 5.0 {671z 0n (0, 5.0)}
   >>> a.data[0] = 6
   >>> a.save()  # compressed to uncompressed
   True
   >>> a = feb.fetch('foo')
   >>> a
   foo uf 6.0 {671z 0n (0, 6.0)}
   >>> a.data[0] = 7
   >>> a.save()  # uncompressed to uncompressed
   True
   >>> a = feb.fetch('foo')
   >>> a
   foo uf 7.0 {671z 0n (0, 7.0)}
   >>> a.data[0] = 2
   >>> a.data[1] = 3
   >>> a.save()  # uncompressed to compressed
   True
   >>> a = feb.fetch('foo')
   >>> a
   foo zf 5.0 {670z 0n (0, 2.0), (1, 3.0)}
   >>> feb.delete('foo')
   >>> feb.commit()

Duplicate fragments are rejected:

   >>> jan.begin()
   >>> a = jan.create('foo')
   >>> b = jan.create('foo')
   >>> a.save()
   True
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
   length 1416 hours
   fragment 2015-01-01
   shard 0
     f10 uf 66.0 {743z 0n (0, 66.0)}
   shard 1
   shard 2
   shard 3
     f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 {671z 0n (0, 55.0)}
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 {671z 0n (671, 44.0)}

You can also prune at save time, in which case pruned data will never touch
the database:

   >>> jan.begin()
   >>> a = jan.create('pruneme')
   >>> a.save(ignore=KEEP_THRESHOLD)
   False
   >>> a = jan.create('keepme')
   >>> a.data[0] = 77
   >>> a.save(ignore=KEEP_THRESHOLD)
   True
   >>> jan.commit()
   >>> ds.dump()
   length 1416 hours
   fragment 2015-01-01
   shard 0
     f10 uf 66.0 {743z 0n (0, 66.0)}
   shard 1
   shard 2
     keepme uf 77.0 {743z 0n (0, 77.0)}
   shard 3
     f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 {671z 0n (0, 55.0)}
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 {671z 0n (671, 44.0)}

Note, however, that pruning during save time can leave erroneous data if the
fragment already exists.

   >>> jan.begin()
   >>> a = jan.fetch('f10')
   >>> a.data[0] = 1                  # change will be lost
   >>> a                              # total not updated yet
   f10 uf 66.0 {743z 0n (0, 1.0)}
   >>> a.save(ignore=KEEP_THRESHOLD)
   False
   >>> jan.commit()
   >>> ds.dump()                      # note old value of f10
   length 1416 hours
   fragment 2015-01-01
   shard 0
     f10 uf 66.0 {743z 0n (0, 66.0)}
   shard 1
   shard 2
     keepme uf 77.0 {743z 0n (0, 77.0)}
   shard 3
     f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 {671z 0n (0, 55.0)}
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 {671z 0n (671, 44.0)}

Complete time series can be queried. Note that missing fragments are filled
with zeroes, but series where all fragments have been pruned return not found.

   >>> print(u.fmt_sparsearray(ds.fetch('f11')))
   {1413z 0n (0, 11.0), (2, 22.0), (1415, 44.0)}
   >>> print(u.fmt_sparsearray(ds.fetch('d01')))
   {1415z 0n (744, 55.0)}
   >>> ds.fetch('f00')
   Traceback (most recent call last):
     ...
   db.Not_Enough_Rows_Error: series not found
   >>> list(ds.fetch_many(['f11']))
   [('f11', array([ 11.,   0.,  22., ...,   0.,   0.,  44.], dtype=float32))]
   >>> list(ds.fetch_many(['d01']))
   [('d01', array([ 0.,  0.,  0., ...,  0.,  0.,  0.]))]
   >>> list(ds.fetch_many(['f00']))
   []
   >>> pprint(list(ds.fetch_many(['f11', 'd01', 'f00'])))
   [('d01', array([ 0.,  0.,  0., ...,  0.,  0.,  0.])),
    ('f11', array([ 11.,   0.,  22., ...,   0.,   0.,  44.], dtype=float32))]

Zero or more shards can be iterated through. If no shards specified, iterate
through all.

   >>> for ts in ds.fetch_all(0):
   ...    print(ts[0], ts[1].dtype, len(ts[1]), u.fmt_sparsearray(ts[1]))
   d01 float64 1416 {1415z 0n (744, 55.0)}
   f10 float32 1416 {1415z 0n (0, 66.0)}
   >>> for ts in ds.fetch_all(3, 1, 0):
   ...    print(ts[0], ts[1].dtype, len(ts[1]), u.fmt_sparsearray(ts[1]))
   f11 float32 1416 {1413z 0n (0, 11.0), (2, 22.0), (1415, 44.0)}
   d01 float64 1416 {1415z 0n (744, 55.0)}
   f10 float32 1416 {1415z 0n (0, 66.0)}
   >>> for ts in ds.fetch_all():
   ...    print(ts[0], ts[1].dtype, len(ts[1]), u.fmt_sparsearray(ts[1]))
   d01 float64 1416 {1415z 0n (744, 55.0)}
   f10 float32 1416 {1415z 0n (0, 66.0)}
   keepme float32 1416 {1415z 0n (0, 77.0)}
   f11 float32 1416 {1413z 0n (0, 11.0), (2, 22.0), (1415, 44.0)}

Optionally, time series where the only fragment is in the lexically-last tag
can be omitted. This is to accommodate use cases where most fragments have
been pruned, but the last has not.

   >>> print(u.fmt_sparsearray(ds.fetch('f10', last_only=False)))
   {1415z 0n (0, 66.0)}
   >>> ds.fetch('d01', last_only=False)
   Traceback (most recent call last):
     ...
   db.Not_Enough_Rows_Error: series not found
   >>> list(ds.fetch_many(['f10', 'd01'], last_only=False))
   [('f10', array([ 66.,   0.,   0., ...,   0.,   0.,   0.], dtype=float32))]
   >>> for ts in ds.fetch_all(last_only=False):
   ...    print(ts[0], ts[1].dtype, len(ts[1]), u.fmt_sparsearray(ts[1]))
   f10 float32 1416 {1415z 0n (0, 66.0)}
   keepme float32 1416 {1415z 0n (0, 77.0)}
   f11 float32 1416 {1413z 0n (0, 11.0), (2, 22.0), (1415, 44.0)}

A Pandas-based interface is provided as well:

   >>> dsp = Dataset_Pandas(tmp + '/bar', 4, writeable=True)
   >>> jan = dsp.open_month(january)
   >>> jan.begin()
   >>> a = jan.create('foo', fill=np.nan)
   >>> a.data[0:3] = [10, 0, 12]
   >>> a
   foo nf 0.0 {1z 741n (0, 10.0), (2, 12.0)}
   >>> a.save()
   True
   >>> a = jan.create('foo+bar')
   >>> a.data[0:4] = [20, 21, 22, 23]
   >>> a.save()
   True
   >>> a = jan.create('foo+baz')
   >>> a.data[0:4] = [30, 31, 32, 33]
   >>> a.save()
   True
   >>> jan.commit()
   >>> dsp.dump()
   length 744 hours
   fragment 2015-01-01
   shard 0
   shard 1
     foo+bar uf 86.0 {740z 0n (0, 20.0), (1, 21.0), (2, 22.0), (3, 23.0)}
     foo+baz uf 126.0 {740z 0n (0, 30.0), (1, 31.0), (2, 32.0), (3, 33.0)}
   shard 2
   shard 3
     foo uf 22.0 {1z 741n (0, 10.0), (2, 12.0)}
   >>> dsp.index
   PeriodIndex(['2015-01-01 00:00', '2015-01-01 01:00', '2015-01-01 02:00',
                '2015-01-01 03:00', '2015-01-01 04:00', '2015-01-01 05:00',
     ...
                '2015-01-31 20:00', '2015-01-31 21:00', '2015-01-31 22:00',
                '2015-01-31 23:00'],
               dtype='int64', length=744, freq='H')
   >>> dsp.fetch('foo+bar')
   2015-01-01 00:00    20.0
   2015-01-01 01:00    21.0
   2015-01-01 02:00    22.0
   2015-01-01 03:00    23.0
   2015-01-01 04:00     0.0
   2015-01-01 05:00     0.0
   2015-01-01 06:00     0.0
   ...
   2015-01-31 22:00     0.0
   2015-01-31 23:00     0.0
   Freq: H, Name: foo+bar, dtype: float32
   >>> dsp.fetch_many(['foo+bar'])
                     foo+bar
   2015-01-01 00:00     20.0
   2015-01-01 01:00     21.0
   2015-01-01 02:00     22.0
   2015-01-01 03:00     23.0
   2015-01-01 04:00      0.0
   2015-01-01 05:00      0.0
   2015-01-01 06:00      0.0
   ...
   2015-01-31 22:00      0.0
   2015-01-31 23:00      0.0
   <BLANKLINE>
   [744 rows x 1 columns]
   >>> dsp.fetch_many(['nonexistent'])
   Traceback (most recent call last):
     ...
   db.Not_Enough_Rows_Error: no matching series found
   >>> dsp.fetch_many([])
   Traceback (most recent call last):
     ...
   db.Not_Enough_Rows_Error: no matching series found
   >>> dsp.fetch_many(['foo+bar', 'foo+baz', 'nonexistent'])
                     foo+bar  foo+baz
   2015-01-01 00:00     20.0     30.0
   2015-01-01 01:00     21.0     31.0
   2015-01-01 02:00     22.0     32.0
   2015-01-01 03:00     23.0     33.0
   2015-01-01 04:00      0.0      0.0
   2015-01-01 05:00      0.0      0.0
   ...
   2015-01-31 22:00      0.0      0.0
   2015-01-31 23:00      0.0      0.0
   <BLANKLINE>
   [744 rows x 2 columns]
   >>> pd.DataFrame({ s.name: s for s in dsp.fetch_all() })
                      foo  foo+bar  foo+baz
   2015-01-01 00:00  10.0     20.0     30.0
   2015-01-01 01:00   0.0     21.0     31.0
   2015-01-01 02:00  12.0     22.0     32.0
   2015-01-01 03:00   NaN     23.0     33.0
   2015-01-01 04:00   NaN      0.0      0.0
   2015-01-01 05:00   NaN      0.0      0.0
   ...
   2015-01-31 22:00   NaN      0.0      0.0
   2015-01-31 23:00   NaN      0.0      0.0
   <BLANKLINE>
   [744 rows x 3 columns]
   >>> dsp.fetch('notfound')
   Traceback (most recent call last):
     ...
   db.Not_Enough_Rows_Error: no matching series found

The Pandas interface provides automatic normalization and resampling:

   >>> dsp.fetch('foo+bar', normalize=True)
   2015-01-01 00:00    2.000000
   2015-01-01 01:00         inf
   2015-01-01 02:00    1.833333
   2015-01-01 03:00         NaN
   2015-01-01 04:00         NaN
   ...
   2015-01-31 22:00         NaN
   2015-01-31 23:00         NaN
   Freq: H, Name: foo+bar$norm, dtype: float32
   >>> dsp.fetch('foo+bar', resample='D')
   2015-01-01    86.0
   2015-01-02     0.0
   2015-01-03     0.0
   ...
   2015-01-30     0.0
   2015-01-31     0.0
   Freq: D, Name: foo+bar, dtype: float32
   >>> dsp.fetch('foo+bar', normalize=True, resample='D')
   2015-01-01    3.909091
   2015-01-02         NaN
   2015-01-03         NaN
   ...
   2015-01-30         NaN
   2015-01-31         NaN
   Freq: D, Name: foo+bar$norm, dtype: float32
   >>> dsp.fetch_many(['foo+bar', 'foo+baz'], normalize=True, resample='D')
               foo+bar$norm  foo+baz$norm
   2015-01-01      3.909091      5.727273
   2015-01-02           NaN           NaN
   2015-01-03           NaN           NaN
   ...
   2015-01-30           NaN           NaN
   2015-01-31           NaN           NaN
   >>> pd.DataFrame({ s.name: s for s in dsp.fetch_all(normalize=True) })
                     foo+bar$norm  foo+baz$norm
   2015-01-01 00:00      2.000000      3.000000
   2015-01-01 01:00           inf           inf
   2015-01-01 02:00      1.833333      2.666667
   2015-01-01 03:00           NaN           NaN
   2015-01-01 04:00           NaN           NaN
   ...
   2015-01-31 22:00           NaN           NaN
   2015-01-31 23:00           NaN           NaN
   <BLANKLINE>
   [744 rows x 2 columns]
   >>> dsp.fetch('foo', normalize=True)
   Traceback (most recent call last):
     ...
   ValueError: delimiter "+" not found
   >>> dsp.close()

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

Close the dataset:

   >>> ds.close()

Re-open it; data still there. Note that simultaneous writing and reading in
separate datasets is not supported.

   >>> ds2 = Dataset(tmp + '/foo', 4)
   >>> ds2.dump()
   length 1416 hours
   fragment 2015-01-01
   shard 0
     f10 uf 66.0 {743z 0n (0, 66.0)}
   shard 1
   shard 2
     keepme uf 77.0 {743z 0n (0, 77.0)}
   shard 3
     f11 uf 33.0 {742z 0n (0, 11.0), (2, 22.0)}
   fragment 2015-02-01
   shard 0
     d01 ud 55.0 {671z 0n (0, 55.0)}
   shard 1
   shard 2
   shard 3
     f11 uf 44.0 {671z 0n (671, 44.0)}
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
   - tested separately in the script tests:
     - inferring hashmod from existing Dataset
     - non-zero fill
'''

import datetime
import enum
import glob
import itertools
import heapq
import operator
import os
import os.path
import re
import sys
import urllib.parse
import zlib

import numpy as np
import pandas as pd

import db
import hash_
import testable
import time_
import u

c = u.c
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

# Normalization stuff
NZ_DELIM = '+'
NZ_SUFFIX = '$norm'
URL_NAME_RE = re.compile(r'^(.+%s)?(.+?)(%s)?$' % (re.escape(NZ_DELIM),
                                                   re.escape(NZ_SUFFIX)))

def name_norm_suffix(name):
   """Append the normalized time series suffix, e.g.:

        >>> name_norm_suffix('foo')
        'foo$norm'
        >>> name_norm_suffix('foo$norm')
        'foo$norm$norm'"""
   return (name + NZ_SUFFIX)

def name_url_canonicalize(name):
   """Canonicalize percent-encoding in URL and change spaces to underscores,
      with optional namespace prefix and normalization suffix left unchanged.

      The motivation is that people who show up with %20 in Wikipedia URLs
      probably want the underscore version instead. See issue #77.

        >>> name_url_canonicalize('Sandy_Koufax')
        'Sandy_Koufax'
        >>> name_url_canonicalize('en+Sandy_Koufax')
        'en+Sandy_Koufax'
        >>> name_url_canonicalize('en+Sandy%20Koufax')
        'en+Sandy_Koufax'
        >>> name_url_canonicalize('en+Sandy Koufax')
        'en+Sandy_Koufax'
        >>> name_url_canonicalize('Sandy_Koufax$norm')
        'Sandy_Koufax$norm'
        >>> name_url_canonicalize('en+Sandy_Koufax$norm')
        'en+Sandy_Koufax$norm'
        >>> name_url_canonicalize('pt+Doen%C3%A7a_cong%C3%AAnita')
        'pt+Doen%C3%A7a_cong%C3%AAnita'

      Input that is incorrectly encoded has undefined behavior, e.g.:

        >>> name_url_canonicalize('en+Sandy%%20Koufax')
        'en+Sandy%25_Koufax'
        >>> name_url_canonicalize('en+Sandy%25%20Koufax')
        'en+Sandy%25_Koufax'"""
   m = URL_NAME_RE.search(name)
   (prefix, name, suffix) = m.groups(default='')
   name = urllib.parse.unquote(name)
   name = name.replace(' ', '_')
   name = urllib.parse.quote(name)
   return (prefix + name + suffix)

class Fragment_Source(enum.Enum):
   'Where did a fragment come from?'
   n = 1; NEW = 1           # created from scratch
   u = 2; UNCOMPRESSED = 2  # retrieved without compression from the database
   z = 3; COMPRESSED = 3    # decompressed from the database


class Dataset(object):

   __slots__ = ('filename',
                'fragment_tags',
                'groups',
                'hashmod',
                'length',
                'writeable')

   def __init__(self, filename, hashmod=None, writeable=False):
      if (not writeable and not os.path.isdir(filename)):
         raise FileNotFoundError('not a directory: %s' % filename)
      self.filename = filename
      self.hashmod = hashmod
      self.writeable = writeable
      self.groups = dict()
      self.caches_reset()

   @property
   def fragment_tag_first(self):
      return self.fragment_tags[0]

   @property
   def fragment_tag_last(self):
      return self.fragment_tags[-1]

   def assemble(self, fragments):
      fmap = { tag: None for tag in self.fragment_tags }
      fmap.update({ f.group.tag: f for f in fragments })
      for (tag, f) in fmap.items():
         if (f is None):
            fmap[tag] = self.group_get(tag).create(None)
      return np.concatenate([f.data for (tag, f) in sorted(fmap.items())])

   def caches_reset(self):
      'Reset all the caches associated with the groups.'
      # Pull the fragment tags from the filesystem, not self.groups, because
      # some groups may not be open.
      self.fragment_tags = list()
      for gf in sorted(glob.iglob('%s/*.db' % self.filename)):
         self.fragment_tags.append(os.path.split(os.path.splitext(gf)[0])[1])
      # Compute the length from the fragment tags, assuming they are months.
      # If they aren't, this will fail. The obvious thing to do then is open
      # each group and query it for length, but that's a bad idea because we
      # do not want to open groups unless we really need to interact with
      # them. Parallel writes to different groups depend on this.
      self.length = sum(time_.hours_in_month(time_.iso8601_parse(f))
                        for f in self.fragment_tags)

   def close(self):
      for g in self.groups.values():
         g.close()

   def dump(self, *tags):
      print('length %d hours' % self.length)
      for ft in self.fragment_tags:
         if (len(tags) > 0 and ft not in tags):
            print('fragment %s omitted' % ft)
         else:
            print('fragment %s' % ft)
            fg = self.group_get(ft)
            fg.dump()

   def dup(self):
      'Return a read-only clone of myself.'
      return self.__class__(self.filename, self.hashmod)

   def fetch(self, name, last_only=True):
      try:
         return next(self.fetch_many((name,), last_only))[1]
      except StopIteration:
         raise db.Not_Enough_Rows_Error('series not found')

   def fetch_many(self, names, last_only=True):
      # This method is a generator to avoid duplicating the entire result set.
      self.open_all()
      fs = list()
      for g in self.groups.values():
         fs.append(g.fetch_many(names))
         #l.debug('fetched from group %s' % g.tag)
      for (fragment, series) in itertools.groupby(heapq.merge(*fs)):
         series = list(series)
         if (    not last_only
             and len(series) == 1
             and self.fragment_tag_last == series[0].group.tag):
            continue
         yield (fragment.name, self.assemble(series))

   def fetch_all(self, *shards, last_only=True):
      self.open_all()
      if (len(shards) == 0):
         shards = range(self.hashmod)
      for sh in shards:
         # Performance note: Even in last_only==False mode, we still retrieve
         # all the fragments in the last tag, even though we will discard most
         # of them. That is, we are guessing that keeping an orderly iteration
         # pattern is best, even though we won't use most of the results.
         fgs = (g.fetch_all(sh) for g in self.groups.values())
         for (name, fragments) in itertools.groupby(heapq.merge(*fgs),
                                                    lambda x: x.name):
            fragments = list(fragments)
            if (len(fragments) > 1
                or last_only
                or self.fragment_tag_last != fragments[0].group.tag):
               yield (name, self.assemble(fragments))

   def open_all(self):
      for f in self.fragment_tags:
         self.group_get(f)

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
         self.caches_reset()
      return self.groups[tag]

   def shard(self, name):
      return hashf(name) % self.hashmod


class Dataset_Pandas(Dataset):

   __slots__ = ('denoms',
                'ds_mirror',
                'index')

   def caches_reset(self):
      super().caches_reset()
      self.denoms = dict()
      self.ds_mirror = None
      if (len(self.groups) > 0):
         self.index = pd.period_range(self.fragment_tag_first, freq='H',
                                      periods=self.length)
      else:
         self.index = None

   def normalize(self, series):
      # FIXME: In a read-write access pattern, the saved denominator series
      # will get stale. The workaround is to explicitly call caches_reset()
      # when transitioning from reading to writing, but that's lame. The right
      # solution may be to invalidate the denominator caches on first write,
      # but that is not implemented yet.
      denom_name = series.name.split(NZ_DELIM, 1)[0]
      if (series.name == denom_name):
         raise ValueError('delimiter "%s" not found' % NZ_DELIM)
      denom_key = (denom_name, series.index.freq)
      if (denom_key not in self.denoms):
         # Fetch denominator series. Note that we could proactively save
         # denominator series as we encounter them, but that optimizes a rare
         # case, and always fetching reduces the number of code paths.
         if (self.ds_mirror is None):
            self.ds_mirror = self.dup()
         denom = self.ds_mirror.fetch(denom_name)
         if (denom.index.freq != series.index.freq):
            denom = denom.resample(series.index.freq).sum()
         self.denoms[denom_key] = denom
      nseries = series / self.denoms[denom_key]
      nseries.name = name_norm_suffix(series.name)
      return nseries

   def fetch(self, name, *args, **kwargs):
      return self.fetch_many((name,), *args, **kwargs).iloc[:,0]

   def fetch_many(self, names, normalize=False, resample=None, *args, **kwargs):
      '''Memory notes; this method:

         * is inefficient if many of the names are not found, because space is
           allocated in the result to hold them before it is later dropped.

         * needs space for two copies of the result, because DataFrame.drop()
           creates a copy even if inplace=True is specified.

         FIXME: Raises db.Not_Enough_Rows_Error if nothing found, which is
         inconsistent with how Dataset.fetch_many() simply returns an empty
         list. The problem is that we don't know how to put an index on the
         resulting DataFrame until we have at least one time series. There are
         other methods to compute the index that don't require a time series,
         but that's not implemented.'''
      namefunc = name_norm_suffix if normalize else lambda x: x
      out_names = set(namefunc(name) for name in names)
      missing_names = out_names.copy()
      result = None
      for (name, series) in super().fetch_many(names, *args, **kwargs):
         series = pd.Series(series, name=name, index=self.index)
         if (resample):
            series = series.resample(resample).sum()
         if (normalize):
            series = self.normalize(series)
         if (result is None):
            # DataFrame initalization is here because we don't know until here
            # what the right index is.
            result = pd.DataFrame(columns=sorted(out_names), index=series.index,
                                  dtype=series.dtype)
         result.loc[:,series.name] = series
         missing_names.remove(series.name)
      if (result is None):
         raise db.Not_Enough_Rows_Error('no matching series found')
      result.drop(missing_names, axis=1, inplace=True)
      return result

   def fetch_all(self, normalize=False, *args, **kwargs):
      for (name, array) in super().fetch_all(*args, **kwargs):
         series = pd.Series(array, name=name, index=self.index)
         if (not normalize):
            yield series
         else:
            try:
               yield self.normalize(series)
            except ValueError:
               # It was a denominator series; ignore it.
               pass


class Fragment_Group(object):

   __slots__ = ('curs',
                'dataset',
                'db',
                'filename',
                'length',
                'metadata',
                'tag',
                'writeable')

   @property
   def mtime(self):
      if (self.empty_p):
         return 0
      else:
         return u.mtime(self.filename)

   @mtime.setter
   def mtime(self, value):
      os.utime(self.filename, (value, value))

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
      subq = "SELECT * FROM (SELECT 1 AS a FROM data%d LIMIT 1)"
      sql = ("SELECT SUM(a) FROM (%s)"
             % " UNION ".join((subq % i) for i in range(self.dataset.hashmod)))
      return not self.db.get_one(sql)[0]

   def fetch(self, name):
      try:
         return self.fetch_many((name,))[0]
      except IndexError:
         raise db.Not_Enough_Rows_Error('no such row')

   def fetch_all(self, shard):
      for i in self.db.get("""SELECT name, dtype, total, data
                              FROM data%d
                              ORDER BY name""" % shard):
         yield self.deserialize(*i)

   def fetch_many(self, names):
      # Return a list instead of a generator because we want SQLite to be
      # completely out of this fragment before we move on to the next one,
      # e.g., no active cursors.
      results = list()
      by_shard = { i: set() for i in range(self.dataset.hashmod) }
      for name in names:
         by_shard[self.dataset.shard(name)].add(name)
      for (shard, snames) in by_shard.items():
         if (len(snames) == 0):
            continue
         bind = ",".join('?' for i in range(len(snames)))
         sql = """SELECT name, dtype, total, data
                  FROM data%d
                  WHERE name IN (%s)""" % (shard, bind)
         results.extend(self.db.get(sql, snames))
         #l.debug('fetched from shard %d' % shard)
      return sorted(self.deserialize(*row) for row in results)

   def fetch_or_create(self, name, dtype=TYPE_DEFAULT, fill=None):
      '''dtype is only used on create; if fetch is successful, the fragment is
         returned unchanged.'''
      try:
         return self.fetch(name)
      except db.Not_Enough_Rows_Error:
         return self.create(name, dtype, fill)

   def initialize_db(self):
      if (self.db.exists('sqlite_master', "type='table' AND name='metadata'")):
         #l.debug('found metadata table, assuming already initalized')
         if (self.dataset.hashmod is None):
            self.dataset.hashmod = int(self.metadatum_get('hashmod'))
            self.metadata['hashmod'] = self.dataset.hashmod
         if (self.length is None):
            self.length = int(self.metadatum_get('length'))
            self.metadata['length'] = self.length
      else:
         if (not self.writeable):
            raise db.Invalid_DB_Error('cannot initalize in read-only mode')
         #l.debug('initializing')
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

   def metadatum_get(self, key):
      return self.db.get_one("SELECT value FROM metadata WHERE key = ?",
                             (key,))[0]


   def open(self, writeable):
      #l.debug('opening %s, writeable=%s' % (self.filename, writeable))
      self.connect(writeable)
      # We use journal_mode = PERSIST to avoid metadata operations and
      # re-allocation, which can be expensive on parallel filesystems.
      self.db.sql("""PRAGMA cache_size = -%d;
                     PRAGMA synchronous = OFF; """
                  % c.getint('limt', 'sqlite_page_cache_kb'))
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

   def vacuum(self):
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
      #l.debug('validated %d metadata items' % len(self.metadata))


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

   # FIXME: Comparisons are on the name attribute only. This is a little
   # strange, but it is needed in Python 3.4 because heapq.merge() doesn't
   # take a key argument (this was added in 3.5).

   def __eq__(self, other):
      return self.name == other.name
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
      # Therefore, use a plain Python float.
      self.total = float(np.nansum(np.abs(self.data)))


testable.register()
