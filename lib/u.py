# -*- coding: utf-8 -*-

'''
Utility routines, classes, etc. A catch-all.

BUGS / WARNINGS / FIXME:

* This module keeps references to the config and logger objects it returns,
  and then uses them, so the caller should take care to not somehow acquire
  different ones.'''

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

import argparse
import codecs
import collections
import configparser
import cProfile
from datetime import datetime, timedelta
import distutils.spawn
import glob
import gzip
import functools
import inspect
import io
import itertools
import logging
import os
import os.path
import pickle as pickle
from pprint import pprint
import psutil
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
CONFIG_DEFAULT = os.path.expanduser('~/.quacrc')

### Globals ###

# These are set to real values on import (i.e., below), so you can do
# something like:
#
#   import u
#   c = u.c
#   l = u.l
c = None  # config object; set after class def and populated in configure()
l = None  # logging object; see EOF for default

cpath = None  # path of configuration file on the command line

# Root of QUAC installation (set below since we need module_dir)
quacbase = None

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

# Should chatter include timestamps? Set in parse_args().
log_timestamps = True


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


class ArgumentParser(argparse.ArgumentParser):
   '''Add a few arguments common to all QUAC scripts. A group called
      "functionality" is available in .default_group; an additional group of
      common options is added at the end in parse_args().'''

   def __init__(self, **kw):
      kw.update({ 'add_help': False,
                  'formatter_class': argparse.RawTextHelpFormatter })
      super(ArgumentParser, self).__init__(**kw)
      self.default_group = self.add_argument_group('functionality')

   def parse_args(self, args):
      gr = self.add_argument_group('help, etc.')
      gr.add_argument(
         '-h', '--help',
         action='help',
         help='show this help message and exit')
      gr.add_argument(
         '--notimes',
         action='store_true',
         help='omit timestamps from log messages (useful for testing)')
      gr.add_argument(
         '--unittest',
         nargs=0,
         action=testable.Raise_Unittest_Exception,
         help='run unit tests instead of doing real stuff')
      gr.add_argument(
         '--verbose',
         action='store_true',
         help='be more verbose with log output')
      return super(ArgumentParser, self).parse_args(args)


class MyConfigParser(configparser.SafeConfigParser):

   def getpath(self, section, key, rel_file=None):
      '''Return absolutized version of path at key; if specified, the path is
         relative to rel_file, otherwise it's relative to the configuration
         file.'''
      if (rel_file is None):
         rel_file = cpath
      return abspath(self.get(section, key), rel_file)

   def getlist(self, section, key):
      return self.get(section, key).split()

c = MyConfigParser()


class Profiler(object):

   def __init__(self):
      self.prof = cProfile.Profile()
      self.prof.enable()

   def stop(self, name):
      self.prof.disable()
      self.prof.dump_stats(name)


class defaultdict_recursive(collections.defaultdict):
   '''defaultdict which autovivifies arbitrarily deeply. For example:

      >>> a = defaultdict_recursive()
      >>> a[1][1] = 1
      >>> a[1][2][3] = 2
      >>> pprint(a.keys())
      dict_keys([1])
      >>> pprint(a[1].keys())
      dict_keys([1, 2])
      >>> a[1][1]
      1
      >>> a[1][2][3]
      2'''
   # https://groups.google.com/forum/?fromgroups#!topic/comp.lang.python/lRnIhaJKZeo[1-25]
   def __init__(self):
      self.default_factory = type(self)


class Deleted_To_Save_Memory(object):
   'Placeholder for objects removed to save memory, to make errors clearer.'
   pass

class Lock_Error(Exception):
   "Raised when a lock can't be acquired."
   pass

class No_Configuration_Read(Exception):
   'Raised when the location of the config file is needed, but none was read.'
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

def abspath(path, rel_file=None):
   '''Return an absolute version of (non-empty) path. Relative paths are
      relative to the location of file rel_file (which need not actually
      exist); if rel_file is None, then path must be absolute already. For
      example:

      >>> abspath('../lib', '/usr/bin/foo')
      '/usr/lib'
      >>> abspath('/usr/lib/../include', '/usr/bin/foo')
      '/usr/include'
      >>> abspath('/usr/lib/../include')
      '/usr/include'
      >>> abspath('../lib')
      Traceback (most recent call last):
        ...
      ValueError: relative path ../lib requires referent
      >>> abspath('')
      Traceback (most recent call last):
        ...
      ValueError: empty path is invalid'''
   if (len(path) == 0):
      raise ValueError('empty path is invalid')
   if (rel_file is None and path[0] != '/'):
      raise ValueError('relative path %s requires referent' % (path))
   if (path[0] == '/'):
      return os.path.abspath(path)
   else:
      return os.path.abspath('%s/%s' % (os.path.dirname(rel_file), path))

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
   except (AttributeError, ValueError) as x:
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
                       for (k,v) in kwargs.items()
                       if k in valid_kwargs } )

def calling_module(frame_ct):
   '''Return the module object frame_ct levels up in the stack. For example:

      >>> calling_module(0)
      <module 'u' from '.../lib/u.py'>

      Note that what is frame_ct levels up must be a module, not a function or
      something else. For example:

      >>> calling_module(-1)  # calling_module() itself
      Traceback (most recent call last):
        ...
      ValueError: stack level -1 is not a module
      >>> calling_module(1)   # somewhere in doctest
      Traceback (most recent call last):
        ...
      ValueError: stack level 1 is not a module'''
   calling_frame = inspect.stack()[frame_ct+1][0]
   try:
      return sys.modules[calling_frame.f_locals['__name__']]
   except KeyError:
      raise ValueError('stack level %d is not a module' % (frame_ct))

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

def config_read(filename):
   '''Read the given configuration file. Abort with an error message if it
      does not exist.'''
   if (len(c.read(filename)) == 0):
      abort('config file not found: %s' % (filename))

def configure(config_path):
   """Parse configuration files & return the config object; config_path is the
      config file given on the command line. Also adjust the load path as
      specified in the files."""
   global cpath
   config_read(abspath("../misc/default.cfg", __file__))  # 1. default.cfg
   if (config_path is not None):
      # this need to be an absolute path in case we change directories later
      cpath = os.path.abspath(config_path)
      config_read(cpath)                                # 2. from command line
      next_config = c.get("path", "next_config")
      if (next_config != ""):
         assert False, "untested: if you need this, remove assertion & test :)"
         config_read(next_config)                       # 3. chained from 2
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

def glob_maxnumeric(dir_):
   '''Given a directory that has zero or more files named only with digits,
      return the largest integer in those filenames. If there are no such
      filenames, return None.'''
   names = glob.glob('%s/*' % (dir_))
   r = re.compile(r'(^|/)([0-9]+)$')
   try:
      return max(int(m.group(2)) for m in (r.search(i) for i in names) if m)
   except ValueError:
      # no matches
      return None

def groupn(iter_, n):
   '''Generator which returns iterables containing n-size chunks of iterable
      iter_; the final chunk may have size less than n (but not 0). Patterned
      after <http://stackoverflow.com/a/3992918/396038>. E.g.:

      >>> a = range(10)
      >>> b = list(range(10))
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

def intfloatpass(v):
   '''Try to convert v to an int or float, in that order; if either succeeds,
      return the result, else return v unchanged. For example:

      >>> intfloatpass('1')
      1
      >>> intfloatpass('1.0')
      1.0
      >>> intfloatpass('1foo')
      '1foo'
      >>> intfloatpass({})
      {}'''
   try:
      return int(v)
   except ValueError:
      try:
         return float(v)
      except ValueError:
         return v
   except TypeError:
      return v

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

def logging_init(tag, file_=None, stderr_force=False, level=None,
                 verbose_=False, truncate=False):
   '''Set up logging and return the logger object. The basic setup is that we
      log to one of two different files and/or stderr:

      1. If file_ is given, log there. Otherwise, log to the file in config
         variable path.log. If both are given, abort with an error; if
         neither, don't log to a file.

      2. If sys.stderr is a TTY or stderr_force is True, then log to standard
         error regardless of file logging. Otherwise, log to standard error if
         there is no file log.

      3. The default log level is INFO. If level is given, use that level
         regardless of the following. If global variable verbose is set
         (either because parse_args() did it in response to --verbose or the
         verbose_ argument to this function is True), then use DEBUG.

      4. If truncate is given, then truncate the log file before using it.
         (Note this is only allowed for log_file_base.)

      This function can be called more than once. Last call wins. Note that
      truncations happens on each call!'''
   if (verbose_):
      global verbose
      verbose = verbose_
   if (level is None):
      level = logging.DEBUG if verbose else logging.INFO

   # Use "FATAL" instead of "CRITICAL" in logs
   logging.addLevelName(50, 'FATAL')

   global l
   l = logging.getLogger('my_logger')
   l.setLevel(level)
   l.handlers = []  # delete existing handlers, to allow re-init.

   # add tag string to permit logcheck filtering, which applies the same
   # regexes to all files it's watching.
   if (log_timestamps):
      fmt = '%%(asctime)s %s %%(levelname)-8s %%(message)s'
   else:
      fmt = '%s %%(levelname)-8s %%(message)s'
   form = logging.Formatter((fmt % (tag)), '%Y-%m-%d_%H:%M:%S')

   # file logger
   try:
      # FIXME: this is a sloppy test for whether a config file was read and
      # path.log is available. We used to test whether c was None, but then
      # importers can't say "c = u.c".
      if (c.get('path', 'log') == ''):
         file_ = None
      else:
         file_c = path_configured(c.getpath('path', 'log'))
         assert (file_ is None)
         assert (not truncate)
         file_ = file_c
   except (No_Configuration_Read, configparser.NoSectionError):
      # path.log not configured, but that's OK
      pass
   if (file_ is not None):
      if (truncate):
         open(file_, 'w').close()
      flog = logging.FileHandler(file_)
      flog.setLevel(level)
      flog.setFormatter(form)
      l.addHandler(flog)

   # console logger
   #
   # FIXME: We test that sys.stderr has isatty() because under Disco,
   # sys.stderr is a MessageWriter object which does not have the method. Bug
   # reported: https://github.com/discoproject/disco/issues/351
   if (stderr_force
       or (hasattr(sys.stderr, 'isatty') and sys.stderr.isatty())
       or file_ is None):
      clog = logging.StreamHandler(sys.stderr)
      clog.setLevel(level)
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
      ...   return (x * r.randint(0, 10**9))
      >>> f(1)
      144272509
      >>> f(1)
      144272509
      >>> f.reset()
      >>> f(1)
      611178002

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

def memory_use():
   '''Return the amount of virtual memory currently allocated to this process,
      in bytes. For example (note flexibility in results to accomodate
      different operating systems):

      >>> a = 'a' * int(2e9)  # string 2 billion chars long
      >>> 2e9 < memory_use() < 5e9
      True
      >>> del a

      Note: This used to have an option to get peak usage, in addition to
      current usage. However, Macs seem not to be able to do this, and since
      it's not critical information for our uses, that feature was removed.'''
   return psutil.Process(os.getpid()).get_memory_info().vms

def memory_use_log():
   l.debug('virtual memory in use: %s' % (fmt_bytes(memory_use())))

def mkdir_f(path):
   '''Ensure that directory path exists. That is, if path already exists and
      is a directory, do nothing; otherwise, try to create directory path (and
      raise appropriate OSError if that doesn't work.)'''
   if (not os.path.isdir(path)):
      os.mkdir(path)

def module_dir(m=None):
   """Return the directory containing the file defining module m. If m is None
      (the default), return the directory containing the calling module. For
      example:

      >>> u_module = calling_module(0)
      >>> module_dir(u_module)
      '.../lib'
      >>> module_dir()
      '.../lib'"""
   if (m is None):
      m = calling_module(1)
   return os.path.abspath(os.path.dirname(m.__file__))

def mpi_available_p():
   '''Return True if MPI (including mpirun) is avilable in a SLURM allocation,
      False otherwise.'''
   return bool('SLURM_NODELIST' in os.environ
               and distutils.spawn.find_executable('mpirun'))

def path_configured(path):
   if (cpath is None):
      raise No_Configuration_Read()
   return abspath(path, cpath)

def partition_sentinel(iter_, sentinel):
   '''Partition an iterable at the first occurrence of a sentinel; return two
      lists containing each partition. The sentinel is not included in either.
      For example:

      >>> partition_sentinel([1,2,3,4], 2)
      ([1], [3, 4])
      >>> partition_sentinel([1,2,3,4], 'not_in_list')
      ([1, 2, 3, 4], [])
      >>> partition_sentinel([], 2)
      ([], [])
      >>> partition_sentinel([1,2,3,4], 4)
      ([1, 2, 3], [])
      >>> partition_sentinel([1,2,3,4], 1)
      ([], [2, 3, 4])
      >>> partition_sentinel(8675309, 2)
      Traceback (most recent call last):
        ...
      TypeError: 'int' object is not iterable'''
   a = list()
   iter2 = iter(iter_)
   for i in iter2:
      if (i == sentinel):
         break
      a.append(i)
   b = list(iter2)
   return (a, b)

def parse_args(ap, args=sys.argv[1:]):
   '''Parse command line arguments and set a few globals based on the result.
      Note that this function must be called before logging_init().'''
   args = ap.parse_args(args)
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
   try:
      global log_timestamps
      log_timestamps = not args.notimes
   except AttributeError:
      pass
   return args

def pickle_dump(file_, obj):
   t = time.time()
   if (isinstance(file_, str)):
      filename = file_
      if (not filename.endswith(PICKLE_SUFFIX)):
         filename += PICKLE_SUFFIX
      fp = gzip.open(filename, 'wb')
   else:
      filename = '???'
      fp = file_
   pickle.dump(obj, fp, pickle.HIGHEST_PROTOCOL)
   l.debug('pickled %s in %s' % (filename, fmt_seconds(time.time() - t)))

def pickle_load(file_):
   t = time.time()
   if (isinstance(file_, str)):
      filename = file_
      if (os.path.exists(filename)):
         # bare filename exists, try that
         if (filename.endswith(PICKLE_SUFFIX)):
            fp = gzip.open(filename)
         else:
            fp = io.open(filename, 'rb')
      elif (os.path.exists(filename + PICKLE_SUFFIX)):
         # filename plus suffix exists, try that
         fp = gzip.open(filename + PICKLE_SUFFIX)
      else:
         # neither exists
         raise IOError('neither %s nor %s exist'
                       % (filename, filename + PICKLE_SUFFIX))
   else:
      filename = '???'
      fp = file_
   obj = pickle.load(fp)
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
   args = [(int(s) if s.strip() else None) for s in text.split(':')]
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
      range() iterators don't support slicing).'''
   indexes = set()
   for sl in slices:
      indexes.update(list(range(len_))[sl])
   return indexes

def sl_union_fromtext(len_, slicetext):
   """e.g.:

      >>> sorted(sl_union_fromtext(10, '0,2:4,-2:'))
      [0, 2, 3, 8, 9]"""
   return sl_union(len_, *list(map(slp, slicetext.split(','))))

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

def str_to_dict(text):
   '''Convert a whitespace- and colon- separated string to a dict, with values
      as either ints, floats, or strs (whichever converts without exception
      first. For example:

      >>> pprint(str_to_dict('a:b c:1 d:1.0'))
      {'a': 'b', 'c': 1, 'd': 1.0}
      >>> pprint(str_to_dict('a:1 a:2'))
      {'a': 2}
      >>> pprint(str_to_dict(''))
      {}
      >>> pprint(str_to_dict(' '))
      {}
      >>> pprint(str_to_dict(None))
      {}
      >>> pprint(str_to_dict('a::b:c'))
      {'a': ':b:c'}
      >>> pprint(str_to_dict('a:1	\vb:1'))
      {'a': 1, 'b': 1}'''
   if (text is None):
      return dict()
   d = dict()
   for kv in text.split():
      (k, _, v) = kv.partition(':')
      d[k] = intfloatpass(v)
   return d

def StringIO():
   '''Return an in-memory buffer that you can put unicode into and get encoded
      bytes out of (with the buffer attribute). It's much like io.StringIO,
      except that doesn't let you get the encoded bytes.'''
   return io.TextIOWrapper(io.BytesIO(), encoding='utf8')

def without_common_prefix(paths):
   '''Return paths with common prefix removed. For example:

      >>> without_common_prefix(['/a/b/c', '/a/b/doogiehauser'])
      ['c', 'doogiehauser']

      If paths has only one element, strip all directories:

      >>> without_common_prefix(['/a/b'])
      ['b']

      If paths is empty, return the empty list:

      >>> without_common_prefix([])
      []

      If one or more paths are equal to the common prefix, they will become
      the empty string:

      >>> without_common_prefix(['/a/b', '/a/b/c'])
      ['', '/c']'''
   if (len(paths) == 0):
      return list()
   elif (len(paths) == 1):
      return [os.path.basename(paths[0])]
   else:
      strip_ct = 0
      for cvec in zip(*paths):
         if (len(set(cvec)) > 1):
            break
         strip_ct += 1
      return [i[strip_ct:] for i in paths]


def without_ext(filename, ext):
   """Return filename with extension ext (which may or may not begin with a
      dot, and which may contain multiple dots) stripped. Raise ValueError if
      the file doesn't have that extension. For example:

      >>> without_ext('foo.tar.gz', '.tar.gz')
      'foo'
      >>> without_ext('foo.tar.gz', 'tar.gz')
      'foo'
      >>> without_ext('foo.tar.bz2', 'tar.gz')
      Traceback (most recent call last):
        ...
      ValueError: foo.tar.bz2 does not have extension .tar.gz
     """
   if (ext[0] != '.'):
      ext = '.' + ext
   fn_new = re.sub('%s$' % (ext), '', filename)
   if (fn_new == filename):
      raise ValueError('%s does not have extension %s' % (filename, ext))
   return fn_new

def zero_attrs(obj, attrs):
   '''e.g.:

      >>> class A(object):
      ...   pass
      >>> a = A()
      >>> zero_attrs(a, ('a', 'b', 'c'))
      >>> pprint(vars(a))
      {'a': 0, 'b': 0, 'c': 0}'''
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
logging_init('tstng', level=logging.WARNING)

quacbase = os.path.abspath(module_dir() + '/..')


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
>>> sl_union(10)  # no slices
set()
>>> sl_union(0, slp('1'))  # empty list
set()
>>> sorted(sl_union(10, slp('1:4')))  # one slice
[1, 2, 3]
>>> sorted(sl_union(10, slp('1:4'), slp('3')))  # overlapping slices
[1, 2, 3]
>>> sl_union(10, slp('10'))  # fully out of bounds
set()
>>> sl_union(10, slp('9:11'))  # partly out of bounds
{9}
>>> sl_union(10, slp('9'), slp('10'))  # one in, one out
{9}

''')


#  LocalWords:  pformat pprint
