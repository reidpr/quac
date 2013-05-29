'''Some wrappers to make pickled files more convenient.'''

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

# FIXME: __del__() appears to be unreliable?
# http://docs.python.org/reference/datamodel.html#special-method-names

import errno
import fcntl
import io
import cPickle as pickle

import u
import testable


class File(object):

   def __init__(self, filename, default=None, writable=False):
      '''Open the given filename as a pickled object. If writable, then the
         modified file can be saved again. If no file exists, then use default
         as the contents of the pickle.'''
      self.filename = filename
      self.writable = writable
      # if we're read/write, acquire a lock
      if (self.writable):
         u.lock_acquire(self.filename)
         self.locked = True
      # load initial data
      try:
         self.data = pickle.load(io.open(self.filename, 'rb'))
      except IOError, x:
         # If we failed because the file doesn't exist, that's OK if we're
         # writable (i.e., automagically create new files). Otherwise,
         # propagate the error.
         if (self.writable and x.errno == errno.ENOENT):
            self.data = default
         else:
            raise

   def __del__(self):
      self.close()

   def close(self):
      if (self.writable and self.locked):
         u.lock_release(self.filename)

   def commit(self):
      'Write data to disk.'
      assert (self.writable)
      fp = io.open(self.filename, mode='wb')
      pickle.dump(self.data, fp, pickle.HIGHEST_PROTOCOL)


testable.register('''

>>> import os
>>> import tempfile
>>> testfile = tempfile.mktemp()
>>> a = File(testfile, default=[1,2,3], writable=True)
>>> a.data
[1, 2, 3]
>>> a.data.append(4)
>>> a.data
[1, 2, 3, 4]
>>> a.commit()
>>> del a
>>> b = File(testfile)
>>> b.data
[1, 2, 3, 4]
>>> os.unlink(testfile)

''')
