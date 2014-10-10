'Reading spreadsheets.'

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.



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
      >>> pprint(e.data)
      {u'halloween': (Date_Vector('2012-10-26', [ 0.  ,  0.  ,  0.05,  0.05,   nan,  1.  ,   nan,  0.  ,  0.  ,  0.  ]),
                      Date_Vector('2012-10-26', [ True,  True,  True,  True, False,  True, False,  True,  True,  True], dtype=bool)),
       u's@ndy': (Date_Vector('2012-10-26', [ 0. ,  0. ,  nan,  nan,  1. ,  0.2,  0.1,  nan,  0. ,  0. ]),
                  Date_Vector('2012-10-26', [ True,  True, False, False,  True,  True,  True, False,  True,  True], dtype=bool))}
      >>> pprint(e.properties)
      {u'incubation days': 2.0, u'pathogen': u'Halloween'}'''

   def __init__(self, file_=None):
      if (file_ is None):
         assert False, 'unimplemented'
      else:
         book = xlrd.open_workbook(file_)
         sheet = book.sheet_by_index(0)
         headers = sheet.row_values(1)
         # read dates
         assert (headers.index('date') == 0)
         dates = [datetime(*xlrd.xldate_as_tuple(i, book.datemode))
                  for i in sheet.col_values(0, start_rowx=2)
                  if isinstance(i, float)]
         # read time series
         self.data = dict()
         for (i, sname) in enumerate(headers[1:], start=1):
            if (sname == ''):
               break
            values = [j if isinstance(j, float) else None
                      for j in sheet.col_values(i, start_rowx=2)]
            data = math_.Date_Vector.zeros(min(dates), max(dates))
            mask = math_.Date_Vector.zeros(min(dates), max(dates),
                                           dtype=np.bool)
            out_i = 0
            for j in range(len(dates)):
               if (j+1 < len(dates)):
                  duration = time_.days_diff(dates[j+1], dates[j])
               else:
                  duration = 1
               assert (duration > 0)
               v = values[j] / duration if values[j] is not None else None
               for k in range(out_i, out_i + duration):
                  if (v is not None):
                     data[k] = v
                     mask[k] = True
                  else:
                     data[k] = np.nan
                     mask[k] = False
               out_i += duration
            self.data[sname] = (data, mask)
         # read property key/values
         key_idx = headers.index('property')
         val_idx = headers.index('value')
         self.properties = dict((k, v if v != '' else None)
                                for (k, v)
                                in zip(sheet.col_values(key_idx, start_rowx=2),
                                       sheet.col_values(val_idx, start_rowx=2))
                                if k != '')


testable.register('')
