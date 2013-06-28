'Various mathematical routines.'

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

import numbers

import numpy as np

import testable


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



testable.register('')
