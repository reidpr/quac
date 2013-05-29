'''Glue classes to let Python code use the QUACreduce protocol. Subclass Job,
   plus mixins as needed, and then implement the abstract classes.

   Many of these methods refer to *key/value pairs*; the key is a non-None
   string not containing any of the characters prohibited by the QUACreduce
   protocol (or an object that produces this when ``str()`` is called on it),
   and the value is any Python object that can be pickled or None. Similarly,
   *items* have the same constraints as values.

   To invoke a mapper or reducer (yes, this is convoluted):

   0. Connectd standard input and/or standard output as appropriate.
   1. Import the module.
   2. If reducing, set the module variable ``rid`` (reducer ID).
   3. Call :meth:`map_stdinout()` or :meth:`reduce_stdinout()`.

   Invocations are expected to set the module variable `rid` (reducer ID)
   before invoking a reducer. Yes, this is kind of strage.

   Mappers and reducers are *not* thread-safe. Each should run in its own
   process.'''

from abc import ABCMeta, abstractmethod
import base64
import cPickle as pickle
import io
import itertools
import operator
import sys

import testable

# Invokers are expected to set this.
rid = None

# We use a relatively large output buffer size of 512K to be prepared for
# filesystems that use large blocks (e.g., Panasas, some RAID). (See also
# OUTPUT_BUFSIZE in ``hashsplit.c``.)
OUTPUT_BUFSIZE = 524288


class Job(object):
   __metaclass__ = ABCMeta

   def __init__(self):
      # Yes, you can quac() instead of map() ...
      self.quac = self.map

   ## Class methods

   def map_stdinout(class_):
      '''Create a mapper, connect it to input and output, and run it.'''
      job = class_()
      job.infp = io.open(sys.stdin.fileno(), 'rb')
      job.outfp = io.open(sys.stdout.fileno(), 'wb')
      for i in job.map_inputs():
         for kv in job.map(i):
            job.map_write(*kv)

   def reduce_stdinout(class_):
      '''Create a reducer, connect it to input and output, and run it.'''
      job = class_()
      job.infp = io.open(sys.stdin.fileno(), 'rb')
      # We open a new file instead of redirecting stdout so that we can set a
      # large buffer.
      job.outfp = io.open('out/%d' % (rid), 'wb', buffering=OUTPUT_BUFSIZE)
      for kvals in job.reduce_inputs():
         for item in job.reduce(*kvals):
            job.reduce_write(item)

   ## Instance methods

   @abstractmethod
   def map(self, item):
      '''FIXME generator yields key/value pairs'''

   @abstractmethod
   def map_inputs(self):
      '''Generator which reads map input items from the mapper input (i.e.,
         the open file ``self.infp``) and yields them as Python objects.
         Typically, this will be implemented by a mixin (e.g.
         :class:`Line_Input`).'''
      pass

   def map_write(self, key, value):
      '''Write one key/value pair to the mapper output.'''
      self.outfp.write(str(key))
      self.outfp.write('\t')
      self.outfp.write(base64.b64encode(pickle.dumps(value, -1)))
      self.outfp.write('\n')

   @abstractmethod
   def reduce(self, key, values):
      '''Generator which yields zero or more reduced items based upon the key
         and an iterator of one or more corresponding values.'''
      pass

   def reduce_inputs(self):
      '''Generator which yields, for each key in the reducer input, a pair
         containing that key and an iterator of one or more corresponding
         values.'''
      for grp in itertools.groupby((l.partition('\t') for l in self.infp),
                                   key=operator.itemgetter(0)):
         key = grp[0]
         values = (pickle.loads(base64.b64decode(i[2])) for i in grp[1])
         yield (key, values)

   @abstractmethod
   def reduce_write(self, item):
      '''Write one Python object, ``item``, to the reduce output stream (the
         open file ``self.outfp``). Often, this will be implemented by a mixin
         (e.g. :class:`Line_Output`).'''
      pass


class Test_Job(Job):
   'Job with dummy implementations of all the abstract methods, for testing.'
   def map(self, item): pass
   def map_inputs(self): pass
   def reduce(self, key, values): pass
   def reduce_write(self, item): pass


testable.register(r'''

# Test data passing from mapper to reducer.
>>> from cStringIO import StringIO
>>> buf = StringIO()
>>> job = Test_Job()
>>> job.outfp = buf
>>> for kv in [(1, -1), (2, -2), (2, -3), (3, -4), (3, -5), (3, -6)]:
...    job.map_write(*kv)
>>> buf.getvalue()
'1\tgAJK/////y4=\n2\tgAJK/v///y4=\n2\tgAJK/f///y4=\n3\tgAJK/P///y4=\n3\tgAJK+////y4=\n3\tgAJK+v///y4=\n'
>>> buf.seek(0)
>>> job.infp = buf
>>> [(k, list(v)) for (k, v) in job.reduce_inputs()]
[('1', [-1]), ('2', [-2, -3]), ('3', [-4, -5, -6])]

''')
