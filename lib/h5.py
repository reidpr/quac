# Copyright © Los Alamos National Security, LLC, and others.

import glob
import io
import os
import re
import subprocess
import sys

import h5py

import hash_
import testable
import u
l = u.l


DUMP_INDENT = '  '


class Sharded(object):

   __slots__ = ('filename',
                'shard_ct',
                'shards')

   def __init__(self, filename, shard_ct=None, mode='a'):
      self.filename = self.filename_base(filename)
      self.shard_ct = self.count_shards(shard_ct)
      self.shards = list()
      for i in range(self.shard_ct):
         self.shards.append(h5py.File(self.filename_shard(i),
                                      mode=mode,
                                      libver='latest'))

   @staticmethod
   def filename_base(filename):
      '''e.g.:

         >>> Sharded.filename_base('foo')
         'foo'
         >>> Sharded.filename_base('foo.0.h5')
         'foo'
         >>> Sharded.filename_base('foo.8675309.h5')
         'foo'
         >>> Sharded.filename_base('foo.0.h5.bar')
         'foo.0.h5.bar'
      '''
      return re.sub(r'\.\d+\.h5$', '', filename)

   def count_shards(self, proposed_shard_ct):
      existing_shard_ct = len(glob.glob('%s.*.h5' % self.filename))
      if (proposed_shard_ct is None):
         if (existing_shard_ct > 0):
            return existing_shard_ct
         else:
            raise ValueError('cannot infer shard count because no shards exist')
      if (proposed_shard_ct < 1):
         raise ValueError('invalid number of shards: %s' % proposed_shard_ct)
      if (existing_shard_ct == 0 or existing_shard_ct == proposed_shard_ct):
         return proposed_shard_ct
      else:
         raise ValueError('%d shards requested, but %d already exist'
                          % (proposed_shard_ct, existing_shard_ct))

   def close(self, compress=False):
      l.debug('closing %d shards under %s' % (self.shard_ct, self.filename))
      for s in self.shards:
         s.close()

   def compress(self):
      # Since we call an external program, we cannot compress the shards until
      # they're closed.
      if (self.shards[0].name is not None):
         raise ValueError('cannot compress an open shard set')
      # Note that we compress all datasets, not just ones that are large
      # enough (--minimum parameter). This simplifies testing but may increase
      # file size if there are lots of small datasets.
      for i in range(self.shard_ct):
         filename = self.filename_shard(i)
         tmpfile = filename + '_tmp'
         os.rename(filename, tmpfile)
         subprocess.check_call(['h5repack',
                                '--latest',
                                '--minimum', '1',
                                '--filter', 'GZIP=9',
                                tmpfile, filename])
         os.unlink(tmpfile)

   def dump(self, verbose=False):
      'Print my (flushed) contents to stdout.'
      args = ['h5dump']
      if (verbose):
         args.append('-p')
      for (i, s) in enumerate(self.shards):
         print(subprocess.check_output(args + [self.filename_shard(i)],
                                       universal_newlines=True), end='')

   def filename_shard(self, i):
      return '%s.%d.h5' % (self.filename, i)

   def flush(self):
      l.debug('flushing %d shards under %s' % (self.shard_ct, self.filename))
      for s in self.shards:
         s.flush()

   def hash(self, name):
      return hash_.of(name)

   def shard_get(self, name):
      'Return a tuple (index, shard) appropriate for data named name.'
      i = self.hash(name) % self.shard_ct
      return (i, self.shards[i])


def dump(filename, verbose=False):
   'Dump a sharded file (convenience shorthand).'
   # FIXME: It is kind of strange that we open the file ourselves even though
   # we don't read it (h5dump does).
   fp = Sharded(filename, mode='r')
   fp.dump(verbose)
   fp.close()

testable.register('''

# WARNING: Dump results in these tests contain ellipses to cover file paths
# and data types that may change on 32- vs. 64-bit platforms.

>>> import numpy as np
>>> import os
>>> tmp = os.environ['TMPDIR']

# empty file, no shard/extension
>>> a = Sharded(tmp + '/empty', shard_ct=1, mode='w')
>>> a.close()
>>> dump(tmp + '/empty')
HDF5 ".../empty.0.h5" {
GROUP "/" {
}
}

# some items in the file, shard/extension stripped
>>> a = Sharded(tmp + '/full.0.h5', shard_ct=1, mode='w')
>>> root = a.shards[0]
>>> root.attrs['a'] = 'hello'
>>> root.attrs['b'] = 8675309
>>> root.attrs['c'] = np.arange(4, dtype=np.int32)
>>> root.create_dataset('data1', (6,), dtype=np.float32, fillvalue=np.NaN)
<HDF5 dataset "data1": shape (6,), type "<f4">
>>> root['data1'][:4] = np.arange(4, 8)
>>> g = root.create_group('/foo/bar')
>>> g.attrs['d'] = 1
>>> g['data2'] = np.arange(8, 12, dtype=np.int16)
>>> a.close()
>>> dump(tmp + '/full.0.h5')
HDF5 ".../full.0.h5" {
GROUP "/" {
   ATTRIBUTE "a" {
      DATATYPE  H5T_STRING {
         STRSIZE H5T_VARIABLE;
         STRPAD H5T_STR_NULLTERM;
         CSET H5T_CSET_UTF8;
         CTYPE H5T_C_S1;
      }
      DATASPACE  SCALAR
      DATA {
      (0): "hello"
      }
   }
   ATTRIBUTE "b" {
      DATATYPE  H5T_STD_I...LE
      DATASPACE  SCALAR
      DATA {
      (0): 8675309
      }
   }
   ATTRIBUTE "c" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      DATA {
      (0): 0, 1, 2, 3
      }
   }
   DATASET "data1" {
      DATATYPE  H5T_IEEE_F32LE
      DATASPACE  SIMPLE { ( 6 ) / ( 6 ) }
      DATA {
      (0): 4, 5, 6, 7, nan, nan
      }
   }
   GROUP "foo" {
      GROUP "bar" {
         ATTRIBUTE "d" {
            DATATYPE  H5T_STD_I...LE
            DATASPACE  SCALAR
            DATA {
            (0): 1
            }
         }
         DATASET "data2" {
            DATATYPE  H5T_STD_I16LE
            DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
            DATA {
            (0): 8, 9, 10, 11
            }
         }
      }
   }
}
}

# edit attribute and dataset in above file
>>> a = Sharded(tmp + '/full.0.h5', shard_ct=1, mode='a')
>>> root = a.shards[0]
>>> root.attrs['a'] = 'hello world'
>>> root['data1'][4] = np.pi
>>> a.close()
>>> a.dump()
HDF5 ".../full.0.h5" {
GROUP "/" {
   ATTRIBUTE "a" {
      DATATYPE  H5T_STRING {
         STRSIZE H5T_VARIABLE;
         STRPAD H5T_STR_NULLTERM;
         CSET H5T_CSET_UTF8;
         CTYPE H5T_C_S1;
      }
      DATASPACE  SCALAR
      DATA {
      (0): "hello world"
      }
   }
   ATTRIBUTE "b" {
      DATATYPE  H5T_STD_I...LE
      DATASPACE  SCALAR
      DATA {
      (0): 8675309
      }
   }
   ATTRIBUTE "c" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      DATA {
      (0): 0, 1, 2, 3
      }
   }
   DATASET "data1" {
      DATATYPE  H5T_IEEE_F32LE
      DATASPACE  SIMPLE { ( 6 ) / ( 6 ) }
      DATA {
      (0): 4, 5, 6, 7, 3.14159, nan
      }
   }
   GROUP "foo" {
      GROUP "bar" {
         ATTRIBUTE "d" {
            DATATYPE  H5T_STD_I...LE
            DATASPACE  SCALAR
            DATA {
            (0): 1
            }
         }
         DATASET "data2" {
            DATATYPE  H5T_STD_I16LE
            DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
            DATA {
            (0): 8, 9, 10, 11
            }
         }
      }
   }
}
}

# sharded file, flush without crashing, compressed
>>> a = Sharded(tmp + '/sharded', shard_ct=2, mode='w')
>>> for i in range(3):
...    name = 'data%d' % i
...    (j, s) = a.shard_get(name)
...    s[name] = np.zeros(4, dtype=np.int32)
>>> a.flush()
>>> a.dump(True)
HDF5 ".../sharded.0.h5" {
GROUP "/" {
   DATASET "data1" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      STORAGE_LAYOUT {
         CONTIGUOUS
         SIZE 16
         OFFSET 2096
      }
      FILTERS {
         NONE
      }
      FILLVALUE {
         FILL_TIME H5D_FILL_TIME_IFSET
         VALUE  0
      }
      ALLOCATION_TIME {
         H5D_ALLOC_TIME_LATE
      }
      DATA {
      (0): 0, 0, 0, 0
      }
   }
}
}
HDF5 ".../sharded.1.h5" {
GROUP "/" {
   DATASET "data0" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      STORAGE_LAYOUT {
         CONTIGUOUS
         SIZE 16
         OFFSET 2096
      }
      FILTERS {
         NONE
      }
      FILLVALUE {
         FILL_TIME H5D_FILL_TIME_IFSET
         VALUE  0
      }
      ALLOCATION_TIME {
         H5D_ALLOC_TIME_LATE
      }
      DATA {
      (0): 0, 0, 0, 0
      }
   }
   DATASET "data2" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      STORAGE_LAYOUT {
         CONTIGUOUS
         SIZE 16
         OFFSET 2112
      }
      FILTERS {
         NONE
      }
      FILLVALUE {
         FILL_TIME H5D_FILL_TIME_IFSET
         VALUE  0
      }
      ALLOCATION_TIME {
         H5D_ALLOC_TIME_LATE
      }
      DATA {
      (0): 0, 0, 0, 0
      }
   }
}
}
>>> a.shard_get('data3')[1]['data3'] = np.zeros(4, dtype=np.int32)
>>> a.compress()
Traceback (most recent call last):
   ...
ValueError: cannot compress an open shard set
>>> a.close()
>>> a.compress()
>>> a.dump(True)
HDF5 ".../sharded.0.h5" {
GROUP "/" {
   DATASET "data1" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      STORAGE_LAYOUT {
         CHUNKED ( 4 )
         SIZE 11 (1.455:1 COMPRESSION)
      }
      FILTERS {
         COMPRESSION DEFLATE { LEVEL 9 }
      }
      FILLVALUE {
         FILL_TIME H5D_FILL_TIME_IFSET
         VALUE  0
      }
      ALLOCATION_TIME {
         H5D_ALLOC_TIME_INCR
      }
      DATA {
      (0): 0, 0, 0, 0
      }
   }
   DATASET "data3" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      STORAGE_LAYOUT {
         CHUNKED ( 4 )
         SIZE 11 (1.455:1 COMPRESSION)
      }
      FILTERS {
         COMPRESSION DEFLATE { LEVEL 9 }
      }
      FILLVALUE {
         FILL_TIME H5D_FILL_TIME_IFSET
         VALUE  0
      }
      ALLOCATION_TIME {
         H5D_ALLOC_TIME_INCR
      }
      DATA {
      (0): 0, 0, 0, 0
      }
   }
}
}
HDF5 ".../sharded.1.h5" {
GROUP "/" {
   DATASET "data0" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      STORAGE_LAYOUT {
         CHUNKED ( 4 )
         SIZE 11 (1.455:1 COMPRESSION)
      }
      FILTERS {
         COMPRESSION DEFLATE { LEVEL 9 }
      }
      FILLVALUE {
         FILL_TIME H5D_FILL_TIME_IFSET
         VALUE  0
      }
      ALLOCATION_TIME {
         H5D_ALLOC_TIME_INCR
      }
      DATA {
      (0): 0, 0, 0, 0
      }
   }
   DATASET "data2" {
      DATATYPE  H5T_STD_I32LE
      DATASPACE  SIMPLE { ( 4 ) / ( 4 ) }
      STORAGE_LAYOUT {
         CHUNKED ( 4 )
         SIZE 11 (1.455:1 COMPRESSION)
      }
      FILTERS {
         COMPRESSION DEFLATE { LEVEL 9 }
      }
      FILLVALUE {
         FILL_TIME H5D_FILL_TIME_IFSET
         VALUE  0
      }
      ALLOCATION_TIME {
         H5D_ALLOC_TIME_INCR
      }
      DATA {
      (0): 0, 0, 0, 0
      }
   }
}
}

# zero shards
>>> a = Sharded(tmp + '/zeroshards', shard_ct=0, mode='w')
Traceback (most recent call last):
   ...
ValueError: invalid number of shards: 0

# re-open above with wrong number of shards
>>> a = Sharded(tmp + '/sharded', shard_ct=3, mode='w')
Traceback (most recent call last):
   ...
ValueError: 3 shards requested, but 2 already exist

''')
