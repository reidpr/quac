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
# application IMO.)
#
# Finally, there is a "Not Available" API that is growing for NumPy. It was
# apparently planned for 1.7 but was removed. It seems nice, so maybe
# something to use in the future. (E.g., see
# <http://www.compsci.wm.edu/SciClone/documentation/software/math/NumPy/html1.7/reference/arrays.maskna.html>.)

import datetime
import numbers

import numpy as np

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

   def __repr__(self):
      if (self._first_day is not None):
         datestr = "'" + time_.iso8601_date(self.first_day) + "'"
      else:
         datestr = 'None'
      return 'Date_Vector(%s, %s' % (datestr, np.ndarray.__repr__(self)[12:])

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
   def last_day(self):
      if (self._first_day is None):
         return None
      else:
         return self._first_day + datetime.timedelta(days=(len(self) - 1))

   def bi_intersect(self, other):
      '''Shrink myself and other so that our bounds match, and return the new
         vectors in a tuple. E.g.:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
         >>> b = Date_Vector('2013-06-04', np.arange(14, 18))
         >>> (c, d) = a.bi_intersect(b)
         >>> c
         Date_Vector('2013-06-04', [4, 5, 6])
         >>> d
         Date_Vector('2013-06-04', [14, 15, 16])

         If there is no intersection, return (None, None):

         >>> c = Date_Vector('2013-06-07', np.zeros(1))
         >>> a.bi_intersect(c)
         (None, None)'''
      fd_new = max(self.first_day, other.first_day)
      ld_new = min(self.last_day, other.last_day)
      self_new = self.resize(fd_new, ld_new)
      other_new = other.resize(fd_new, ld_new)
      return (self_new, other_new)

   def bi_union(self, other):
      '''Extend myself and other so that our bounds match, and return the new
         vectors in a tuple. E.g.:

         >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
         >>> b = Date_Vector('2013-06-04', np.arange(4, 8))
         >>> (c, d) = a.bi_union(b)
         >>> c
         Date_Vector('2013-06-02', [2, 3, 4, 5, 6, 0])
         >>> d
         Date_Vector('2013-06-02', [0, 0, 4, 5, 6, 7])'''
      fd_new = min(self.first_day, other.first_day)
      ld_new = max(self.last_day, other.last_day)
      self_new = self.resize(fd_new, ld_new)
      other_new = other.resize(fd_new, ld_new)
      return (self_new, other_new)

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

# def similarity(a, a_start, b, b_start,
#                mask=None, mask_start=None, metric=cosine):
#    '''Return the similarity, in the range [0,1], of ``Date_Vector``\ s a and
#       b. mask is a boolean validity Date_Vector; mask[i] is True if a[i] and
#       b[i] are valid data, False otherwise. All three vectors are NumPy
#       arrays. metric '''
#    assert (mask is not None), 'mask is None not implemented'


testable.register('''

# test that Date_Vector objects can be pickled
>>> import cPickle as pickle
>>> a = Date_Vector('2013-06-02', np.arange(2, 7))
>>> b = pickle.loads(pickle.dumps(a))
>>> np.array_equal(a, b)
True
>>> a.first_day == b.first_day
True
>>> b.last_day == b.last_day
True

''')
