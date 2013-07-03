# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

'''For each input n-gram occurring more than min_occur number of times,
   compute a time series of occurrences per day.

   Each output item's key is the n-gram, and the value is a dictionary with
   the following structure::

     { 'ngram':      <the ngram as a unicode object>,
       'total':      <total number of occurrences as an integer>,
       'series':     <Date_Vector containing the time series> }

   Note that the n-gram is redundantly encoded (as the key and as part of the
   value). This is so that values can be independently used without retaining
   the corresponding key.'''


import collections

import numpy as np

from . import base
import math_
import time_
import tok.unicode_props


class Tweet_Job(base.TSV_Input_Job, base.KV_Pickle_Seq_Output_Job):

   def __init__(self, params):
      base.Job.__init__(self, params)
      self.tzer = tok.unicode_props.UP_Tiny(self.params['n'])

   def map(self, fields):
      # WARNING: make sure field indices match any file format changes
      date = fields[1][:10]  # first 10 characters of ISO 8601 string is date
      for token in self.tzer.tokenize(fields[2]):  # tweet text
         yield (token, date)

   def reduce(self, ngram, dates):
      cts = collections.Counter()
      first_day = '9999-00-99'
      last_day = '0000-00-00'
      for date in dates:
         first_day = min(first_day, date)
         last_day = max(last_day, date)
         cts[date] += 1
      total = sum(cts.itervalues())
      if (total >= self.params['min_occur']):
         first_day = time_.dateify(first_day)
         last_day = time_.dateify(last_day)
         assert (first_day <= last_day)
         # use float32 for space efficiency at the expense of precision
         ct_series = math_.Date_Vector.zeros(first_day, last_day,
                                             dtype=np.float32)
         for (date, ct) in cts.iteritems():
            date = time_.dateify(date)
            ct_series[time_.days_diff(date, first_day)] = ct
         yield (ngram, { 'ngram': ngram,
                         'total': total,
                         'series': ct_series })
