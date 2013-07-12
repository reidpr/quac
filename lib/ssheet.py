'Reading spreadsheets.'

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

from __future__ import division

from datetime import datetime
import os.path
from pprint import pprint

import numpy as np
import xlrd

import math_
import testable
import time_
import u


class Excel(object):
   '''For example:

      >>> e = Excel(file_=(u.module_dir() + '/../misc/halloween.xls'))
      >>> e.data
      Date_Vector('2012-10-28', [ 0.05,  0.05,   nan,  1.  ,   nan,  0.  ,  0.  ,  0.  ])
      >>> e.mask
      Date_Vector('2012-10-28', [ True,  True, False,  True, False,  True,  True,  True], dtype=bool)
      >>> pprint(e.properties)
      {u'incubation days': 2.0, u'pathogen': u'Halloween'}'''

   def __init__(self, file_=None):
      if (file_ is None):
         assert False, 'unimplemented'
      else:
         book = xlrd.open_workbook(file_)
         sheet = book.sheet_by_index(0)
         headers = sheet.row_values(1)
         # read time series and mask
         assert (headers.index('date') == 0)
         dates = [datetime(*xlrd.xldate_as_tuple(i, book.datemode))
                  for i in sheet.col_values(0, start_rowx=2)
                  if isinstance(i, float)]
         values = [i if isinstance(i, float) else None
                   for i in sheet.col_values(1, start_rowx=2)]
         self.data = math_.Date_Vector.zeros(min(dates), max(dates))
         self.mask = math_.Date_Vector.zeros(min(dates), max(dates),
                                             dtype=np.bool)
         out_i = 0
         for i in xrange(len(dates)):
            if (i+1 < len(dates)):
               duration = time_.days_diff(dates[i+1], dates[i])
            else:
               duration = 1
            assert (duration > 0)
            v = values[i] / duration if values[i] is not None else None
            for j in xrange(out_i, out_i + duration):
               if (v is not None):
                  self.data[j] = v
                  self.mask[j] = True
               else:
                  self.data[j] = np.nan
                  self.mask[j] = False
            out_i += duration
         # read property key/values
         key_idx = headers.index('property')
         val_idx = headers.index('pvalue')
         self.properties = dict((k, v if v != '' else None)
                                for (k, v)
                                in zip(sheet.col_values(key_idx, start_rowx=2),
                                       sheet.col_values(val_idx, start_rowx=2))
                                if k != '')


testable.register('')
