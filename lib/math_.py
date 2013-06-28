'Various mathematical routines.'

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

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
   '''NumPy array of daily values that knows its start date and can
      grow/shrink itself given target dates. For example:

      # create
      >>> a = Date_Vector('2013-06-02', np.arange(2, 7))
      >>> a
      Date_Vector([2, 3, 4, 5, 6])
      >>> a.first_day
      datetime.date(2013, 6, 2)
      >>> a.last_day
      datetime.date(2013, 6, 6)

      # shrink
      >>> b = a.shrink('2013-06-03', None)
      >>> b
      Date_Vector([3, 4, 5, 6])
      >>> b.first_day
      datetime.date(2013, 6, 3)
      >>> b.last_day
      datetime.date(2013, 6, 6)
      >>> a.shrink(None, '2013-06-04')
      Date_Vector([2, 3, 4])
      >>> a.shrink('2013-06-03', '2013-06-04')
      Date_Vector([3, 4])
      >>> a.shrink(None, None)
      Date_Vector([2, 3, 4, 5, 6])
      >>> a.shrink('2013-06-06', None)
      Date_Vector([6])
      >>> a.shrink(None, '2013-06-02')
      Date_Vector([2])
      >>> b = a.shrink('2013-06-07', None)
      >>> b
      Date_Vector([], dtype=int64)
      >>> b.first_day  # None
      >>> b.last_day   # None
      >>> a.shrink(None, '2013-06-01')
      Date_Vector([], dtype=int64)

      # some errors
      >>> a.shrink('2013-06-01', None)
      Traceback (most recent call last):
        ...
      ValueError: shrink() cannot grow
      >>> a.shrink(None, '2013-06-07')
      Traceback (most recent call last):
        ...
      ValueError: shrink() cannot grow

      Notes:

      1. You must manually create and pass in a standard NumPy array; this is
         so you can use all the fancy constructors (in addition to being much
         easier to implement).

      2. The first day argument can either be a datetime.date object or a
         string in ISO 8601 format.

      3. You can pass None for the first day, but nothing will work right
         until you set the first_day attribute.'''

   # There is some weirdness here because NumPy arrays are weird. See
   # <http://docs.scipy.org/doc/numpy/user/basics.subclassing.html>. We follow
   # the "slightly more realistic example" pattern.

   def __new__(class_, first_day, input_array):
      o = np.asarray(input_array).view(class_)
      o.first_day = first_day
      return o

   def __array_finalize__(self, o):
      if (o is None):
         return
      self.first_day = getattr(o, 'first_day', None)

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

   def shrink(self, first_day, last_day):
      '''Return a copy of myself with bounds first_day and last_day, which
         must be equal to or smaller than the current bounds. If either is
         None, pass through existing bound. Trim elements outside bounds. If
         the new bounds cross, return an empty vector.'''
      first_day = time_.dateify(first_day)
      last_day = time_.dateify(last_day)
      if (first_day is None):
         first_day = self.first_day
      if (last_day is None):
         last_day = self.last_day
      if (first_day < self.first_day or last_day > self.last_day):
         raise ValueError('shrink() cannot grow')
      if (max(first_day, self.first_day) > min(last_day, self.last_day)):
         return Date_Vector(None, np.array([], dtype=self.dtype))
      trim_start = time_.days_diff(first_day, self.first_day)
      last_idx = time_.days_diff(last_day, self.first_day)
      assert (trim_start >= 0)
      assert (last_idx >= 0)
      return Date_Vector(max(first_day, self.first_day),
                         self[trim_start:last_idx + 1])

# def similarity(a, a_start, b, b_start,
#                mask=None, mask_start=None, metric=cosine):
#    '''Return the similarity, in the range [0,1], of ``Date_Vector``\ s a and
#       b. mask is a boolean validity Date_Vector; mask[i] is True if a[i] and
#       b[i] are valid data, False otherwise. All three vectors are NumPy
#       arrays. metric '''
#    assert (mask is not None), 'mask is None not implemented'


testable.register('')
