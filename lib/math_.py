'Various mathematical routines.'

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

# A few implementation notes:
#
# Many Date_Vector operations are masked, i.e., there is a parallel boolean
# vector saying which data are valid and which aren't. Therefore, it seems
# logical to subclass numpy.ma.MaskedArray instead of numpy.ndarray. However,
# we subclass the latter.
#
# The main reason for this is that many vectors share the same mask.
# MaskedArray objects each carry around their own mask, and AFAICT full masks
# are stored even if they're empty (i.e., no elements are excluded). This
# redundant storage wastes space and adds a consistency problem.
#
# (MaskedArrays are also rather slow, but not enough that it matters for this
# application IMO. In face, we use them in some of our computations.)
#
# Finally, there is a "Not Available" API that is growing for NumPy. It was
# apparently planned for 1.7 but was removed. It seems nice, so maybe
# something to use in the future. (E.g., see
# <http://www.compsci.wm.edu/SciClone/documentation/software/math/NumPy/html1.7/reference/arrays.maskna.html>.)

from __future__ import division

import datetime
import numbers
import sys

import numpy as np
from numpy import ma

import testable
import time_


### Misc ###

def is_power_2(i):
   '''Return True if i is a positive power of two, false otherwise. This
      relies on a common bit-twiddling trick; see e.g.
      <http://stackoverflow.com/a/600306/396038>. For example:

      >>> is_power_2(0)
      False
      >>> is_power_2(1)
      True
      >>> is_power_2(3)
      False
      >>> is_power_2(4)
      True'''
   assert (isinstance(i, numbers.Integral))
   assert (i >= 0)
   return (i > 0) and ((i & (i - 1)) == 0)


### Vector similarity ###

class Date_Vector(np.ndarray):
   '''NumPy array of daily values that knows its start date and a few related
      operations. For example:

      >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
      >>> a
      Date_Vector('2013-06-02', [2, 3, 4, 5, 6])
      >>> a.first_day
      datetime.date(2013, 6, 2)
      >>> a.last_day
      datetime.date(2013, 6, 6)

      Notes:

      1. You must manually create and pass in a standard NumPy array; this is
         so you can use all the fancy constructors (in addition to being much
         easier to implement).

      2. The first day argument can either be a datetime.date object or a
         string in ISO 8601 format.

      3. You can pass None for the first day, but nothing will work right
         until you set the first_day attribute.'''

   # The basic idea here is that we have a sequence of contiguous, uniformly
   # sized time intervals, each with an associated scalar value. For example,
   # a vector of with day intervals might something like this:
   #
   #   |     8      |     6      |     7      |     5      |
   #   +------------+------------+------------+------------+
   #   | 2013-06-02 | 2013-06-03 | 2013-06-04 | 2013-06-05 |
   #
   #   first_day = 2013-06-02
   #   last_day  = 2012-06-05
   #
   # There are a couple of issues to keep in mind.
   #
   # First, is the ending bound (here, last_day) inclusive or exclusive? We've
   # opted for inclusive.
   #
   # Second, when the interval is assumed to be one day -- which is currently
   # the case -- then last_day really does contain an *interval*. Currently,
   # we use datetime.date objects.
   #
   # This become more complicated when, as is expected, we extend to vectors
   # with arbitrarily-sized (though still uniform) intervals. Then, we'll need
   # first_interval and last_interval attributes that are datetime.datetime
   # objects; i.e., these attributes now contain an *instant* rather than an
   # interval (really they are a 1-microsecond interval, but that's close
   # enough). So some decisions will have to be made.
   #
   # One way to do it would be to have first_interval and last_interval refer
   # to the *beginning* of the relevant intervals (and this confuses the
   # exclusive/inclusive issue slightly). For example, suppose we have
   # intervals of one hour:
   #
   #   |   8    |   6   |   7   |   5   |
   #   +--------+-------+-------+-------+
   #   ^        ^       ^       ^
   #   1:33 pm  2:33pm  3:33pm  4:33pm
   #
   #   first_interval = 2013-06-02T13:33:00.000000
   #   last_interval =  2013-06-02T16:33:00.000000  (even though the vector
   #                                                 really extends to 5:33pm
   #                                                 minus epsilon)

   # There is some weirdness in class creation because NumPy arrays are weird.
   # See <http://docs.scipy.org/doc/numpy/user/basics.subclassing.html>. We
   # follow the "slightly more realistic example" pattern.

   def __new__(class_, first_day, input_array):
      o = np.asarray(input_array).view(class_)
      o.first_day = first_day
      return o

   def __array_finalize__(self, o):
      if (o is None):
         return
      self.first_day = getattr(o, 'first_day', None)

   # Yet more weirdness to enable functions that return scalars to actually do
   # so, rather than returning 0-rank arrays. See
   # <http://stackoverflow.com/questions/16805987/>.

   def __array_wrap__(self, o):
      if (len(o.shape) == 0):
         return o[()]
      else:
         return np.ndarray.__array_wrap__(self, o)

   # Pickling also requires some hoops. This follows the example attached to
   # <http://thread.gmane.org/gmane.comp.python.numeric.general/14809>.

   def __reduce__(self):
      state = list(np.ndarray.__reduce__(self))
      state[2] = (state[2], (self._first_day, ))
      return tuple(state)

   def __setstate__(self, state):
      (super_state, my_state) = state
      np.ndarray.__setstate__(self, super_state)
      (self._first_day, ) = my_state

   # other special methods

   def __repr__(self):
      if (self._first_day is not None):
         datestr = "'" + time_.iso8601_date(self.first_day) + "'"
      else:
         datestr = 'None'
      return 'Date_Vector(%s, %s' % (datestr, np.ndarray.__repr__(self)[12:])

   def __str__(self):
      return self.__repr__()

   @staticmethod
   def bi_union(*vectors):
      '''Extend vectors so that their bounds match, and return the new vectors
         in an iterable. E.g.:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
         >>> b = Date_Vector('2013-06-04', np.arange(4, 8))
         >>> (c, d) = Date_Vector.bi_union(a, b)
         >>> c
         Date_Vector('2013-06-02', [2, 3, 4, 5, 6, 0])
         >>> d
         Date_Vector('2013-06-02', [0, 0, 4, 5, 6, 7])

         If any vectors are None, pass through those Nones:

         >>> tuple(Date_Vector.bi_union(None, a))
         (None, Date_Vector('2013-06-02', [2, 3, 4, 5, 6]))
         >>> tuple(Date_Vector.bi_union(None))
         (None,)'''
      v_nonnone = [v for v in vectors if v is not None]
      if (len(v_nonnone) > 0):
         fd_new = min(v.first_day for v in v_nonnone)
         ld_new = max(v.last_day for v in v_nonnone)
      return ((v.resize(fd_new, ld_new) if v is not None else None)
              for v in vectors)

   @staticmethod
   def bi_intersect(*vectors):
      '''Shrink vectors so that their bounds match, and return the new vectors
         in an iterable. E.g.:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
         >>> b = Date_Vector('2013-06-04', np.arange(14, 18))
         >>> (c, d) = Date_Vector.bi_intersect(a, b)
         >>> c
         Date_Vector('2013-06-04', [4, 5, 6])
         >>> d
         Date_Vector('2013-06-04', [14, 15, 16])

         If there is no intersection, return an iterable of Nones:

         >>> c = Date_Vector('2013-06-07', np.zeros(1))
         >>> tuple(Date_Vector.bi_intersect(a, c))
         (None, None)

         If any vectors are None, pass through those Nones:

         >>> tuple(Date_Vector.bi_intersect(None, a))
         (None, Date_Vector('2013-06-02', [2, 3, 4, 5, 6]))
         >>> tuple(Date_Vector.bi_intersect(None))
         (None,)'''
      v_nonnone = [v for v in vectors if v is not None]
      if (len(v_nonnone) > 0):
         fd_new = max(v.first_day for v in v_nonnone)
         ld_new = min(v.last_day for v in v_nonnone)
      return ((v.resize(fd_new, ld_new) if v is not None else None)
              for v in vectors)

   @classmethod
   def zeros(class_, first_day, last_day, **kwargs):
      '''Create a Date_Vector with the given first_day and last_day containing
         zeros. Keyword arguments are passed unchanged to :func:`np.zeros()`.
         For example:

         >>> a = Date_Vector.zeros('2013-06-02', '2013-06-05')
         >>> a
         Date_Vector('2013-06-02', [ 0.,  0.,  0.,  0.])
         >>> a.dtype
         dtype('float64')

         >>> Date_Vector.zeros('2013-06-02', '2013-06-05', dtype=np.bool)
         Date_Vector('2013-06-02', [False, False, False, False], dtype=bool)

         If last_day is earlier than first_day, then return None:

         >>> Date_Vector.zeros('2013-06-02', '2013-06-01') is None
         True'''
      o_tmp = class_(first_day, np.zeros(1, **kwargs))
      return o_tmp.resize(first_day, last_day)

   @property
   def first_day(self):
      return self._first_day
   @first_day.setter
   def first_day(self, x):
      self._first_day = time_.dateify(x)

   @property
   def iso8601iter(self):
      '''Iterator which lists my days in ISO 8601 format. For example:

         >>> a = Date_Vector.zeros('2013-06-02', '2013-06-05')
         >>> a.iso8601iter
         <generator object iso8601iter at 0x...>
         >>> list(a.iso8601iter)
         ['2013-06-02', '2013-06-03', '2013-06-04', '2013-06-05']'''
      for d in time_.dateseq(self.first_day, self.last_day):
         yield time_.iso8601_date(d)

   @property
   def last_day(self):
      if (self._first_day is None):
         return None
      else:
         return self._first_day + datetime.timedelta(days=(len(self) - 1))

   def bounds_eq(self, other):
      'Return True if I have the same bounds as other.'
      return (self.first_day == other.first_day and len(self) == len(other))

   def bounds_le(self, other):
      '''Return True if I have the same or smaller bounds than other, False
         otherwise. For example:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
         >>> b = Date_Vector('2013-06-02', np.arange(2, 6))
         >>> c = Date_Vector('2013-06-03', np.arange(3, 7))
         >>> a.bounds_le(a)
         True
         >>> a.bounds_le(b)
         False
         >>> b.bounds_le(a)
         True
         >>> a.bounds_le(c)
         False
         >>> c.bounds_le(a)
         True'''
      return (self.first_day >= other.first_day
              and self.last_day <= other.last_day)

   def date(self, i):
      '''Return the date of index i. For example:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
         >>> a.date(0)
         datetime.date(2013, 6, 2)
         >>> a.date(5)
         datetime.date(2013, 6, 7)'''
      return self.first_day + datetime.timedelta(days=i)

   def grow_to(self, other):
      '''Return a copy of myself grown to match the bounds of the larger of
         myself and other. For example:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 5))
         >>> b = Date_Vector('2013-06-03', np.arange(3, 6))
         >>> a.grow_to(b)
         Date_Vector('2013-06-02', [2, 3, 4, 0])
         >>> b.grow_to(a)
         Date_Vector('2013-06-02', [0, 3, 4, 5])'''
      return self.resize(min(self.first_day, other.first_day),
                         max(self.last_day, other.last_day))

   def normalize(self, other, parts_per=1):
      '''Divide self by other over the range where the bounds intersect. E.g.:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 5))
         >>> b = Date_Vector('2013-06-01', np.arange(1, 6)*2)
         >>> a
         Date_Vector('2013-06-02', [2, 3, 4])
         >>> b
         Date_Vector('2013-06-01', [ 2,  4,  6,  8, 10])
         >>> a.normalize(b)
         Date_Vector('2013-06-02', [ 0.5,  0.5,  0.5])
         >>> a.normalize(b, parts_per=1e6)
         Date_Vector('2013-06-02', [ 500000.,  500000.,  500000.])
         '''
      assert (self.bounds_le(other)), 'unimplemented'
      return parts_per * (self / other.shrink_to(self))

   def resize(self, first_day, last_day):
      '''Return a copy of myself with new bounds first_day and last_day.

         >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
         >>> a
         Date_Vector('2013-06-02', [2, 3, 4, 5, 6])

         Shrinking removes the newly extra elements (note that if either bound
         is None, we use the existing bound):

         >>> s = a.resize('2013-06-03', None)
         >>> s
         Date_Vector('2013-06-03', [3, 4, 5, 6])
         >>> a.resize(None, '2013-06-04')
         Date_Vector('2013-06-02', [2, 3, 4])
         >>> a.resize('2013-06-03', '2013-06-04')
         Date_Vector('2013-06-03', [3, 4])
         >>> a.resize('2013-06-06', None)
         Date_Vector('2013-06-06', [6])
         >>> a.resize(None, '2013-06-02')
         Date_Vector('2013-06-02', [2])

         If the new bounds cross, return None:

         >>> a.resize('2013-06-07', None) is None
         True
         >>> a.resize(None, '2013-06-01') is None
         True

         If shrinking, the result may (but is not guaranteed to) be a view of
         the original vector:

         >>> np.may_share_memory(a, s)
         True

         Growing adds new elements containing zero:

         >>> g = a.resize('2013-06-01', '2013-06-07')
         >>> g
         Date_Vector('2013-06-01', [0, 2, 3, 4, 5, 6, 0])
         >>> a.resize('2013-06-01', None)
         Date_Vector('2013-06-01', [0, 2, 3, 4, 5, 6])
         >>> a.resize(None, '2013-06-07')
         Date_Vector('2013-06-02', [2, 3, 4, 5, 6, 0])

         You can grow and shrink at the same time:

         >>> gs = a.resize('2013-06-01', '2013-06-05')
         >>> gs
         Date_Vector('2013-06-01', [0, 2, 3, 4, 5])
         >>> a.resize('2013-06-03', '2013-06-07')
         Date_Vector('2013-06-03', [3, 4, 5, 6, 0])

         Grown vectors are not views:

         >>> np.may_share_memory(a, g)
         False
         >>> np.may_share_memory(a, gs)
         False

         Finally, it's OK to do a no-op resize. In this case, the result is a
         shallow copy.

         >>> n = a.resize(None, None)
         >>> n
         Date_Vector('2013-06-02', [2, 3, 4, 5, 6])
         >>> n is a
         False
         >>> np.may_share_memory(a, n)
         True'''
      # clean up new bounds
      fd_new = time_.dateify(first_day) or self.first_day
      ld_new = time_.dateify(last_day) or self.last_day
      # if they're empty, return None
      if (max(fd_new, self.first_day) > min(ld_new, self.last_day)):
         return None
      # how many elements to add and remove from the start?
      delta_start = time_.days_diff(fd_new, self.first_day)
      trim_start = max(0, delta_start)
      add_start = max(0, -delta_start)
      # how many elements to add and remove from the end?
      delta_end = time_.days_diff(self.last_day, ld_new)
      trim_end = max(0, delta_end)
      add_end = max(0, -delta_end)
      # Do it!
      if (add_start == 0 and add_end == 0):
         # If shrinking, don't use hstack(); this avoids copying data, which
         # favors speed over memory. The caller can do a deep copy if this is
         # a problem.
         return Date_Vector(fd_new, self[trim_start:len(self) - trim_end])
      else:
         return Date_Vector(fd_new,
                            np.hstack([np.zeros(add_start, dtype=self.dtype),
                                       self[trim_start:len(self) - trim_end],
                                       np.zeros(add_end, dtype=self.dtype)]))

   def shrink_to(self, other):
      '''Return a copy of myself shrunk to match the bounds of the smaller of
         myself and other. For example:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 5))
         >>> b = Date_Vector('2013-06-03', np.arange(3, 6))
         >>> a.shrink_to(b)
         Date_Vector('2013-06-03', [3, 4])
         >>> b.shrink_to(a)
         Date_Vector('2013-06-03', [3, 4])

         If there is no overlap, return None:

         >>> a.shrink_to(Date_Vector.zeros('2013-06-05', '2013-06-05')) is None
         True'''
      return self.resize(max(self.first_day, other.first_day),
                         min(self.last_day, other.last_day))


def pearson(a, b, a_mask=None, b_mask=None, min_data=3):
   '''Given two Date_Vectors a and b, return their Pearson correlation.

      >>> a = Date_Vector('2013-06-02', np.array((1,    2,    3,    5   )))
      >>> b = Date_Vector('2013-06-02', np.array((0.11, 0.12, 0.13, 0.15)))
      >>> pearson(a, b)
      1.0

      If a_mask and/or b_mask are non-None, they should be boolean
      Date_Vectors that are True when the corresponding data element is valid
      and False otherwise:

      >>> c = Date_Vector('2013-06-02', np.array((0.11, 0.12, 9999, 0.15)))
      >>> cm = Date_Vector('2013-06-02', np.array((True, True, False, True)))
      >>> pearson(a, c)
      0.097593...
      >>> pearson(a, c, b_mask=cm)
      1.0

      Masks must be a superset of the corresponding vectors:

      >>> m = Date_Vector('2013-06-02', np.array((True, True, True)))
      >>> pearson(a, b, a_mask=m)
      Traceback (most recent call last):
        ...
      ValueError: mask must have equal or greater bounds than vector
      >>> pearson(a, b, b_mask=m)
      Traceback (most recent call last):
        ...
      ValueError: mask must have equal or greater bounds than vector

      The mask need not be boolean:

      >>> m = Date_Vector('2013-06-02', np.array((0.1, 0.1, 0.1, 0.1)))
      >>> pearson(a, b, a_mask=m)
      1.0

      a and b need not have any particular shared length or first_day. If they
      share fewer than min_data valid data, due either to masking or bounds,
      return 0 (i.e., if we don't have enough information to compute
      correlation, assume there is none):

      >>> bm = Date_Vector('2013-06-02', np.array((True, False, False, True)))
      >>> pearson(a, b, b_mask=bm, min_data=2)
      1.0
      >>> pearson(a, b, b_mask=bm, min_data=3)
      0.0
      >>> d = Date_Vector('2013-06-04', np.array((0.11, 0.12, 0.13, 0.15)))
      >>> pearson(a, d)
      0.0

      Similarly, if the variance of either a or b is zero, though the
      correlation in this case is actually undefined, return 0:

      >>> e = Date_Vector('2013-06-02', np.array((42, 42, 42, 42)))
      >>> pearson(a, e)
      0.0
      >>> pearson(e, a)
      0.0'''
   # Implemented per <http://en.wikipedia.org/wiki/Pearson_correlation>.
   def maskify(x, mask):
      'Promote x to a MaskedArray if mask is not None.'
      if (mask is None):
         return x
      else:
         assert x.bounds_eq(mask)
         assert (mask.dtype == np.bool)
         # We invert the mask because MaskedArray has made the baffling choice
         # that True mask elements correspond to *in*valid data. This is the
         # opposite of every other mask I've seen...
         return ma.array(x, mask=~mask)
   # line up all the bounds and masks
   if ((a_mask is not None and not a.bounds_le(a_mask))
       or (b_mask is not None and not b.bounds_le(b_mask))):
      raise ValueError('mask must have equal or greater bounds than vector')
   (a, b, a_mask, b_mask) = Date_Vector.bi_intersect(a, b, a_mask, b_mask)
   ab_mask = Date_Vector(a.first_day, np.ones(len(a), dtype=np.bool))
   if (a_mask is not None):
      ab_mask *= a_mask
   if (b_mask is not None):
      ab_mask *= b_mask
   if (len(a) < min_data or ab_mask.sum() < min_data):
      return 0.0
   # do some computin'
   a = maskify(a, ab_mask)
   b = maskify(b, ab_mask)
   a_mean = a.mean()
   b_mean = b.mean()
   covar = np.sum(ab_mask * (a - a_mean) * (b - b_mean), dtype=np.float64)
   a_stddev = np.sqrt(np.sum((a - a_mean)**2))
   b_stddev = np.sqrt(np.sum((b - b_mean)**2))
   if (a_stddev == 0 or b_stddev == 0):
      return 0.0
   return covar / (a_stddev * b_stddev)


testable.register('''

# test that Date_Vector objects can be pickled
>>> import cPickle as pickle
>>> a = Date_Vector('2013-06-02', np.arange(2, 7))
>>> b = pickle.loads(pickle.dumps(a))
>>> np.array_equal(a, b)
True
>>> a.first_day == b.first_day
True

# make sure repr() objects really can be eval()'ed
>>> b = eval(repr(a))
>>> np.array_equal(a, b)
True
>>> a.first_day == b.first_day
True

# do methods that should return scalars do so?
>>> c = np.arange(2, 7)
>>> c.sum()
20
>>> type(c.sum())
<type 'numpy.int64'>
>>> a.sum()
20
>>> type(a.sum())
<type 'numpy.int64'>

''')
