# Stuff to facilitate running multicore jobs. The basic philosophy here is to
# spawn a few large jobs instead of many small jobs, repacking small jobs into
# bigger ones if needed.

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.


from __future__ import division

import itertools
import sys

import joblib

import testable
import u


# How many cores to use? Use init() to set.
core_ct = 1


def do(f, every, each, require_multicore=False):
   '''Parallelized call of f on the arguments given in the sequence each
      (either a sequence of argument tuples of a sequence of single
      arguments). The arguments in tuple every are passed before each. If
      require_multicore, then raise ValueError if core_ct == 1 (this is mostly
      for testing). The return value is a list of return values of each call.
      E.g. (see below for f_test()):

      >>> do(f_test, (1, 2, 4), [8, 16])
      [15, 23]
      >>> do(f_test, (1, 2), [(4, 8), (16, 32)])
      [15, 51]

      Note: Objects are passed between processes by pickling and unpickling.
      Obviously, this means that the arguments must be picklable. However, it
      also means that argument size should be minimized, especially in each.'''
   assert (isinstance(every, tuple))
   if (require_multicore and core_ct == 1):
      raise ValueError('multicore forced, but core_ct == 1')
   eaches = u.chunker(each, core_ct)
   results = (joblib.Parallel(n_jobs=core_ct)
              (joblib.delayed(hickenlooper)(f, every, t) for t in eaches))
   return list(itertools.chain(*results))

def f_test(a, b, c, d):
   '''Function to test do(). It's here rather than in the doctest because only
      module-level functions (???) can be passed to joblib; otherwise, you get
      "TypeError: can't pickle function objects".'''
   return (a + b + c + d)

def hickenlooper(f, every, each):
   '''e.g.:

      >>> def f(a, b, c):
      ...   return (a + b + c)
      >>> hickenlooper(f, (1, 2), ((3,), (4,), (5,)))
      [6, 7, 8]'''
   # If each isn't a sequence of tuples, wrap it.
   if (not isinstance(each[0], tuple)):
      each = [(i,) for i in each]
   return [f(*(every + args)) for args in each]

def init(core_ct_):
   '''This is here because doctest is not able to set module globals without
      fooling around (this is by design). Perhaps in the future it will have a
      real purpose as well. You do not need to call it, as there are sensible
      defaults (in particular, core_ct = 1 -- you must ask for parallelism).'''
   assert (core_ct_ >= 1)
   global core_ct
   core_ct = core_ct_


testable.register('''

# Does require_multicore work?
>>> init(1)
>>> do(f_test, (1, 2), [(4, 8), (16, 32)])
[15, 51]
>>> do(f_test, (1, 2), [(4, 8), (16, 32)], require_multicore=True)
Traceback (most recent call last):
  ...
ValueError: multicore forced, but core_ct == 1
>>> init(2)
>>> do(f_test, (1, 2), [(4, 8), (16, 32)], require_multicore=True)
[15, 51]

# Don't crash if the length of every is less than core_ct
>>> init(4)
>>> do(f_test, (1, 2), [(1, 1), (2, 2), (3, 3)])
[5, 7, 9]

''')
