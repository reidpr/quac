# Utility routines for the Twitter analysis package
#
# BUGS / WARNINGS / FIXME:
#
# * This module keeps references to the config and logger objects it returns,
#   and then uses them, so the caller should take care to not somehow acquire
#   different ones.

import codecs
import collections
import ConfigParser
from datetime import datetime, timedelta
import gzip
import functools
import inspect
import itertools
import logging
import numbers
import os
import cPickle as pickle
import pytz
import random
import re
import sys
import time

import numpy as np

import multicore
import testable


### Constants ###

PICKLE_SUFFIX = '.pkl.gz'
WGS84_SRID = 4326  # FIXME: redundantly defined in geo/srs.py


### Globals ###

c = None  # configuration object
l = None  # logging object; see end of file for default

cpath = None  # path of configuration file on the command line

# A random number generator with known seed. Re-seeded in parse_args().
rand = random.Random(8675309)
rand_np = np.random.mtrand.RandomState(8675309)

# Used for silencing stdout; see stdout_silence() below.
stdout_copy_fno = None

# Python apparently doesn't set the locale correctly on stdout when it's a
# pipe, so this hack gives us a file object that can print UTF8 to stdout
# regardless.
utf8_stdout = codecs.getwriter('utf8')(sys.stdout)

# Should chatter be verbose? Set in parse_args().
verbose = False


### Classes ###

class Accumulator(object):

   '''Memory-efficient class which accumulates a sum and can compute its mean.
      There is also a threshold for minimum number of items before mean
      becomes non-zero. For example:

      >>> a = Accumulator(min_count=3)
      >>> a.mean
      0.0
      >>> a.add(1)
      >>> a.add(2)
      >>> a.mean
      0.0
      >>> a.add(3)
      >>> a.sum_
      6.0
      >>> a.count
      3
      >>> a.mean
      2.0'''

   __slots__ = ('sum_', 'count', 'min_count')

   def __init__(self, sum_=0.0, count=0, min_count=1):
      self.sum_ = sum_
      self.count = count
      self.min_count = min_count

   @property
   def mean(self):
      if (self.count < self.min_count):
         return 0.0
      else:
         return (self.sum_/self.count)

   def add(self, x):
      self.sum_ += x
      self.count += 1

class defaultdict_recursive(collections.defaultdict):
   'defaultdict which autovivifies arbitrarily deeply.'
   # https://groups.google.com/forum/?fromgroups#!topic/comp.lang.python/lRnIhaJKZeo[1-25]
   def __init__(self):
      self.default_factory = type(self)

class Lock_Error(Exception):
   "Raised when a lock can't be acquired."
   pass

class Deleted_To_Save_Memory(object):
   'Placeholder for objects removed to save memory, to make errors clearer.'
   pass


### Functions ###

def abort(text, exc_info=False):
   """Log a fatal error and abort immediately. exc_info is interpreted as for
      the logging functions; see
      http://docs.python.org/library/logging.html#logging.debug. TLDR: pass
      True and the function will figure out what the current exception is and
      log a traceback."""
   l.fatal(text, exc_info=exc_info)
   sys.exit(1)

def class_by_name(name):
   '''Return a class given its fully qualified name.'''
   # http://stackoverflow.com/questions/452969
   parts = name.split('.')
   mname = '.'.join(parts[:-1])
   try:
      m = __import__(mname)
      for p in parts[1:]:
         m = getattr(m, p)
      return m
   except (AttributeError, ValueError), x:
      raise ValueError('Can\'t import "%s": %s' % (name, str(x)))

def call_kw(f, *args, **kwargs):
   '''Call f and return its return value, passing args as well as the kwargs
      which are actually valid for f; this lets you call f with an arbitrary
      kwargs even if f doesn't allow arbitrary kwargs. For example:

      >>> def f(a, b=1, c=2):
      ...    return ('%d %d %d' % (a, b, c))
      >>> call_kw(f, 3, b=4, c=5, d=6)
      '3 4 5'

      Warning: args is *not* checked for matching the function signature. It
      is probably a bad idea to use this wrapper to call functions with a
      non-trivial mix of args and kwargs.'''
   argspec = inspect.getargspec(f)
   valid_kwargs = set(argspec.args[-len(argspec.defaults):])
   return f(*args, **{ k:v
                       for (k,v) in kwargs.iteritems()
                       if k in valid_kwargs } )

def chunker(seq, p):
   '''Split sequence seq into p more or less equal sized sublists. If p <
      len(seq), then return len(seq) sublists of length 1. E.g.:

      >>> chunker('abcdefghijklm', 3)
      ['abcde', 'fghi', 'jklm']
      >>> chunker('abc', 4)
      ['a', 'b', 'c']
      >>> chunker('', 1)
      []

      See also groupn().'''
   # based on http://code.activestate.com/recipes/425397
   new = []
   n = len(seq) // p                   # min items per subsequence
   r = len(seq) % p                    # remaindered items
   (b, e) = (0, n + min(1, r))         # first split
   for i in range(min(p, len(seq))):
      new.append(seq[b:e])
      r = max(0, r-1)                  # use up remainders
      (b, e) = (e, e + n + min(1, r))  # min(1,r) is always 0 or 1
   return new

def configure(config_path):
   """Parse configuration files & return the config object; config_path is the
      config file given on the command line. Also adjust the load path as
      specified in the files."""
   global c
   global cpath
   c = ConfigParser.SafeConfigParser()
   c.read(path_relative(__file__, "default.cfg"))  # 1. default.cfg
   if (config_path is not None):
      # this need to be an absolute path in case we change directories later
      cpath = os.path.abspath(config_path)
      c.read(cpath)                                # 2. from command line
      next_config = c.get("path", "next_config")
      if (next_config != ""):
         assert False, "untested: if you need this, remove assertion & test :)"
         c.read(next_config)                       # 3. chained from 2
      pythonpath_append = c.get('path', 'pythonpath_append')
      if (pythonpath_append):
         sys.path.append(path_configured(pythonpath_append))
   return c

def copyupdate(template, updates):
   '''Return a copy of dict template with updates applied. E.g.:

      >>> a = {1:2, 3:4}
      >>> copyupdate(a, {3:5, 5:6})
      {1: 2, 3: 5, 5: 6}
      >>> a
      {1: 2, 3: 4}'''
   r = template.copy()
   r.update(updates)
   return r

def groupn(iter_, n):
   '''Generator which returns iterables containing n-size chunks of iterable
      iter_; the final chunk may have size less than n (but not 0). Patterned
      after <http://stackoverflow.com/a/3992918/396038>. E.g.:

      >>> a = xrange(10)
      >>> b = range(10)
      >>> [list(i) for i in groupn(a, 3)]
      [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
      >>> [list(i) for i in groupn(b, 3)]
      [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
      >>> [list(i) for i in groupn(a, 5)]
      [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]
      >>> [list(i) for i in groupn(a, 99999)]
      [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]

      See also chunker().'''
   # FIXME: It is kind of lame that this returns lists. Any way we can return
   # generators or iterables instead?
   q = iter(iter_)  # new iterator so we can "destructively" remove items
   while True:
      chunk = list(itertools.islice(q, 0, n))
      if (len(chunk) == 0):
         return
      yield chunk

def is_power_2(i):
   """Return True if i is a positive power of two, false otherwise. This
      relies on a common bit-twiddling trick; see
      http://stackoverflow.com/questions/600293/how-to-check-if-a-number-is-a-power-of-2
      among many other sources."""
   assert (isinstance(i, numbers.Integral))
   return (i > 0) and ((i & (i - 1)) == 0)

def lock_acquire(name):
   '''Try to acquire the lock *name*. Only one process can have the lock at
      once. Return immediately if the lock was acquired, otherwise raise
      Lock_Error. In the latter case, there are no side effects. Locks must be
      explicitly released with lock_release().'''
   # FIXME: Better to do this with fcntl.lockf() or some third party library?
   try:
      os.mkdir(name + '.lock')
   except OSError:
      raise Lock_Error("can't acquire lock '%s'" % (name))

def lock_release(name):
   '''Release the lock *name*. If the lock was not previously acquired, raise
      an exception. (FIXME: You can currently release locks acquired by other
      processes and delete unrelated directories.) See also lock_acquire().'''
   os.rmdir(name + '.lock')

def logging_init(tag, level=logging.DEBUG, verbose_=None):
   "Set up logging and return the logger object."

   # Reset verbose argument?
   if (verbose_ is not None):
      global verbose
      verbose = verbose_

   # FIXME: filthy hack to print "FATAL" instead of "CRITICAL" in logs
   logging._levelNames[50] = 'FATAL'

   # FIXME: This config is pretty awkward... any way to do it with a
   # dictionary or file (string) config?
   global l
   l = logging.getLogger('my_logger')
   l.setLevel(level)  # maximum of logger and handler level is used

   # Delete existing handlers, to allow re-init.
   l.handlers = []

   # add tag string to permit logcheck filtering, which applies the same
   # regexes to all files it's watching.
   form = logging.Formatter(("%%(asctime)s %s %%(levelname)-8s %%(message)s"
                             % (tag)),
                            "%Y-%m-%d_%H:%M:%S")
   # file logger which is more concise
   do_file_logger = (c is not None and c.get('path', 'log'))
   if (do_file_logger):
      flog = logging.FileHandler(path_configured(c.get("path", "log")))
      flog.setLevel(logging.INFO)
      flog.setFormatter(form)
      l.addHandler(flog)
   # console logger which is more verbose
   if (sys.stdout.isatty() or not do_file_logger):
      clog = logging.StreamHandler()
      clog.setLevel(logging.DEBUG if verbose else logging.INFO)
      clog.setFormatter(form)
      l.addHandler(clog)
   return l

def memoize(f):
   '''Decorator that memoizes a function; i.e., if the function is called
      again with the same arguments, the cached value is returned and the
      function is not really called. Resettable. Fails with TypeError if you
      pass an unhashable argument. Can't wrap functions that take keyword
      arguments. For example:

      >>> import random
      >>> r = random.Random(1)
      >>> @memoize
      ... def f(x):
      ...   return (x * r.randint(0, 99))
      >>> f(1)
      13
      >>> f(1)
      13
      >>> f.reset()
      >>> f(1)
      84

      (Note that the above should work for plain functions too, but it's a
      class method because doctest is getting confused.)'''
   # Adapted <http://wiki.python.org/moin/PythonDecoratorLibrary#Memoize>.
   # This uses some weird voodoo I don't quite understand.

   f.cache = dict()

   def reset():
      # for some reason f.cache = dict() doesn't stick
      f.cache.clear()
   f.reset = reset

   @functools.wraps(f)
   def wrapper(*args):
      if (args not in f.cache):
         f.cache[args] = f(*args)
      return f.cache[args]

   return wrapper

def memory_use(peak=False):
   '''Return the amount of virtual memory currently (if when == 'now') or at
      most (if when == 'peak') allocated to this process, in bytes. E.g.:

      >>> a = 'a' * int(2e9)  # string 2 billion chars long
      >>> big = memory_use()
      >>> fmt_bytes(big)
      '...GiB'
      >>> del a
      >>> small = memory_use()
      >>> peak = memory_use(peak=True)
      >>> big > small
      True
      >>> big == peak
      True'''
   # Based on http://stackoverflow.com/a/898406/396038
   ss = open('/proc/self/status').read()
   field = 'VmPeak' if peak else 'VmSize'
   m = re.search(r'^%s:\s+(\d+) kB' % field, ss, re.MULTILINE)
   if (m):
      return int(m.group(1)) * 1024
   else:
      l.warn('memory usage unsupported on this architecture')
      return 1

def memory_use_log():
   l.debug('virtual memory used: %s now, %s peak'
           % (fmt_bytes(memory_use()), fmt_bytes(memory_use(True))))


def path_configured(path):
   return path_relative(cpath, path)

def path_relative(rel_file, path):
   '''Return an absolute version of path, which is relative to the location of
      file rel_file. Paths beginning with / are not allowed.'''
   assert (path[0] != '/')
   return os.path.abspath('%s/%s' % (os.path.dirname(rel_file), path))

def parse_args(ap):
   '''Parse command line arguments and set a few globals based on the result.
      Note that this function must be called before logging_init().'''
   args = ap.parse_args()
   try:
      multicore.init(args.cores)
   except AttributeError:
      pass
   try:
      rand.seed(args.random_seed)
      rand_np.seed(args.random_seed)
   except AttributeError:
      pass
   try:
      global verbose
      verbose = args.verbose
   except AttributeError:
      pass
   return args

def pickle_dump(filename, obj):
   t = time.time()
   if (not filename.endswith(PICKLE_SUFFIX)):
      filename += PICKLE_SUFFIX
   pickle.dump(obj, gzip.open(filename, 'wb'), pickle.HIGHEST_PROTOCOL)
   l.debug('pickled %s in %s' % (filename, fmt_seconds(time.time() - t)))

def pickle_load(filename):
   t = time.time()
   if (not filename.endswith(PICKLE_SUFFIX)):
      filename += PICKLE_SUFFIX
   obj = pickle.load(gzip.open(filename))
   l.debug('unpickled %s in %s' % (filename, fmt_seconds(time.time() - t)))
   return obj

def slp(text):
   '''Parse a Python index or slice notation and return a slice object. A bare
      index (no colons) gets you a slice returning a one-element list with
      that index (or an empty list if out-of-bounds) -- this is different than
      calling slice() with that argument. An empty string gets you an empty
      list. For example:

      >>> a = [0, 1, 2, 3]
      >>> a[slp('1:3')]
      [1, 2]
      >>> a[1:3]
      [1, 2]
      >>> a[slp('2')]
      [2]
      >>> a[slice(2)]
      [0, 1]
      >>> [a[2]]
      [2]
      >>> a[slp('')]
      []'''
   # see http://stackoverflow.com/questions/680826/
   args = map(lambda s: (int(s) if s.strip() else None), text.split(':'))
   if (len(args) == 1 and args[0] is None):
      return slice(0)
   elif (len(args) == 1 and isinstance(args[0], int)):
      start = args[0]
      stop = start + 1 if (start != -1) else None
      return slice(start, stop)
   else:
      return slice(*args)

def sl_union(len_, *slices):
   '''Given a sequence length and some slices, return the sequence of indexes
      which form the union of the given slices. For example:

      >>> sorted(sl_union(10, slp('0'), slp('2:4'), slp('-2:')))
      [0, 2, 3, 8, 9]

      Note that this function instantiates lists of length len_ (because
      xrange() iterators don't support slicing).'''
   indexes = set()
   for sl in slices:
      indexes.update(range(len_)[sl])
   return indexes

def sl_union_fromtext(len_, slicetext):
   '''e.g.:

      >>> sorted(sl_union_fromtext(10, '0,2:4,-2:'))
      [0, 2, 3, 8, 9]'''
   return sl_union(len_, *map(slp, slicetext.split(',')))

def stdout_restore():
   global stdout_copy_fno
   os.dup2(stdout_copy_fno, 1)
   # WARNING: Voodoo! This sets stdout to be line-buffered.
   sys.stdout = os.fdopen(1, 'w', 1)
   stdout_copy_fno = None

def stdout_silence():
   '''Some libraries (we're looking at you, SpatiaLite!) print junk to stdout
      when they're loaded. This function will silence that output, even if
      it's coming from outside Python. Use stdout_unsilence() to put things
      back to normal.'''
   # http://stackoverflow.com/questions/4178614
   devnull = open('/dev/null', 'w')
   global stdout_copy_fno
   stdout_copy_fno = os.dup(sys.stdout.fileno())
   sys.stdout.flush()
   os.dup2(devnull.fileno(), 1)

def utcnow():
   'Return an "aware" datetime for right now in UTC.'
   # http://stackoverflow.com/questions/4530069
   return datetime.now(pytz.utc)

def without_ext(filename):
   """Return filename with extension, if any, stripped, e.g:

      >>> without_ext('/foo/bar.gz')
      '/foo/bar'
      >>> without_ext('/foo/bar')
      '/foo/bar'"""
   return os.path.splitext(filename)[0]

def zero_attrs(obj, attrs):
   '''e.g.:

      >>> class A(object):
      ...   pass
      >>> a = A()
      >>> zero_attrs(a, ('a', 'b', 'c'))
      >>> sorted(vars(a).items())
      [('a', 0), ('b', 0), ('c', 0)]'''
   for attr in attrs:
      setattr(obj, attr, 0)


# Functions to format numbers with K, M, etc. suffixes.
# e.g.: fmt_bytes(2048) -> 2KiB
#
# Partly based on http://stackoverflow.com/questions/1094841

def fmt_seconds(num):
   return str(timedelta(seconds=int(round(num))))

def fmt_si(num):
   return fmt_real(num, 1000, ["", "k", "M", "G", "T", "P"])

def fmt_bytes(num):
   return fmt_real(num, 1024, ["B", "KiB", "MiB", "GiB", "TiB", "PiB"])

def fmt_real(num, factor, units):
   assert num >= 0, "negative numbers unimplemented"
   factor = float(factor)
   for unit in units:
      if (num < factor):
         return ("%.1f%s" % (num, unit))
      num /= factor
   assert False, "number too large"


# Default logger to allow testing. You should never actually see output from
# this unless tests fail.
logging_init('tstng', logging.WARNING)


testable.register('''

# Make sure random seed is set to a known value
>>> rand.random()
0.40224696110279223

# Memoized function fails with TypeError if passed an unhashable argument.
>>> @memoize
... def f(x):
...   return x*2
>>> f(dict())
Traceback (most recent call last):
  ...
TypeError: unhashable type: 'dict'

# Check that memoized reset() works by looking at exposed cache.
>>> f(1)
2
>>> f.cache
{(1,): 2}
>>> f.reset()
>>> f.cache
{}

# More slices. Basically, we want (almost) the same behavior as if we had
# typed the slice into the Python interpreter. The "and None" trick is simply
# to suppress output if the expression is true, so we don't have to keep
# typing "True".
>>> a = [0, 1, 2, 3, 4]
>>> (a[slp(':')] == a) and None
>>> (a[slp('0')] == [a[0]]) and None
>>> (a[slp('4')] == [a[4]]) and None
>>> a[slp('5')]
[]
>>> (a[slp('-1')] == [a[-1]]) and None
>>> (a[slp('-2')] == [a[-2]]) and None
>>> (a[slp('-5')] == [a[-5]]) and None
>>> a[slp('-6')]
[]
>>> (a[slp('1:')] == a[1:]) and None
>>> (a[slp(':1')] == a[:1]) and None
>>> (a[slp('-2:')] == a[-2:]) and None
>>> (a[slp(':-2')] == a[:-2]) and None
>>> (a[slp('1::')] == a[1::]) and None
>>> (a[slp('::1')] == a[::1]) and None
>>> (a[slp('2::')] == a[2::]) and None
>>> (a[slp('::2')] == a[::2]) and None
>>> (a[slp('-1::')] == a[-1::]) and None
>>> (a[slp('::-1')] == a[::-1]) and None

# More unioned slices
>>> sorted(sl_union(10))  # no slices
[]
>>> sorted(sl_union(0, slp('1')))  # empty list
[]
>>> sorted(sl_union(10, slp('1:4')))  # one slice
[1, 2, 3]
>>> sorted(sl_union(10, slp('1:4'), slp('3')))  # overlapping slices
[1, 2, 3]
>>> sorted(sl_union(10, slp('10')))  # fully out of bounds
[]
>>> sorted(sl_union(10, slp('9:11')))  # partly out of bounds
[9]
>>> sorted(sl_union(10, slp('9'), slp('10')))  # one in, one out
[9]

''')
