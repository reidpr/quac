# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

'''For each input n-gram occurring more than min_occur number of times,
   compute a time series of occurrences per day.

   Each output item's key is the n-gram, and the value is a dictionary with
   the following structure::

     { 'ngram':      <the ngram as a unicode object>,
       'first_day':  <first day of the series as a datetime.datetime object>,
       'last_day':   <last day of the time series>,
       'total':      <total number of occurrences as an integer>,
       'series':     <NumPy array containing the time series> }

   Note that the n-gram is redundantly encoded (as the key and as part of the
   value). This is so that values can be independently used without retaining
   the corresponding key.'''


import collections

from . import base
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
      first_day = '9999-99-99'
      last_day = '0000-00-00'
      for date in dates:
         first_day = min(first_day, date)
         last_day = max(last_day, date)
         cts[date] += 1
      total = sum(cts.itervalues())
      ct_series = cts  # FIXME: convert to NumPy array
      if (total >= self.params['min_occur']):
         yield (ngram, { 'ngram': ngram,
                         'first_day': time_.iso8601_parse(first_day),
                         'last_day': time_.iso8601_parse(last_day),
                         'total': total,
                         'series': ct_series })
