# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.
# -*- coding: utf-8 -*-

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
import datetime
import sys
import urllib

import numpy as np

from . import base
import math_
import ssheet
import tok.unicode_props
import tsv_glue
import tweet
import u
import wikimedia


class Build_Job(base.KV_Pickle_Seq_Output_Job):

   def reduce(self, ngram, datecounts):
      cts = collections.Counter()
      first_day = float('+inf')
      last_day = float('-inf')
      for (date, count) in datecounts:
         first_day = min(first_day, date)
         last_day = max(last_day, date)
         cts[date] += count
      total = sum(cts.itervalues())
      if (total >= self.params['min_occur']):
         assert (first_day <= last_day)
         # use float32 for space efficiency at the expense of precision
         first_dt = datetime.date.fromordinal(first_day)
         last_dt = datetime.date.fromordinal(last_day)
         ct_series = math_.Date_Vector.zeros(first_dt, last_dt,
                                             dtype=np.float32)
         for (date, ct) in cts.iteritems():
            ct_series[date - first_day] = ct
         yield (ngram, { 'ngram': ngram,
                         'total': total,
                         'series': ct_series })


class Correlate_Job(base.KV_Pickle_Seq_Input_Job, base.TSV_Output_Job):

   def map_init(self):
      self.total_vec = u.pickle_load(self.params['total_file'])['series']
      mask = np.array([tweet.is_enough(self.total_vec.date(i),
                                       self.total_vec[i],
                                       sample_rate=self.params['sample_rate'])
                       for i in xrange(len(self.total_vec))],
                      dtype=bool)
      if (mask.sum() < 0.5 * len(mask)):
         u.abort('too few valid n-gram days (%d of %d); check sample rate?'
                 % (mask.sum(), len(mask)))
      self.total_mask = math_.Date_Vector(self.total_vec.first_day, mask)
      self.targets = list()
      short_names = u.without_common_prefix(self.params['input_sss'])
      for (sn, ln) in zip(short_names, self.params['input_sss']):
         e = ssheet.Excel(file_=ln)
         for (name, (data, mask)) in e.data.iteritems():
            name = '%s:%s' % (urllib.quote_plus(u.without_ext(sn, '.xls')),
                              urllib.quote_plus(name))
            self.targets.append({ 'name': name,
                                  'data': data,
                                  'mask': mask })

   def map(self, kv):
      (_, ngram) = kv
      for t in self.targets:
         # Extend the ngram series to match the target, to make sure that
         # leading and trailing zeroes are not lost.
         ng_vec = ngram['series'].grow_to(t['data'])
         ng_vec = ng_vec.normalize(self.total_vec, parts_per=1e6)
         peak = ng_vec.max()
         trough = ng_vec.min()
         # Ignore series with a peak that is too low.
         if (peak < self.params['min_ppm']):
            continue
         # Compute correlation.
         assert (t['data'].bounds_eq(t['mask']))
         r = math_.pearson(ng_vec, t['data'],
                           self.total_mask, t['mask'])
         if (abs(r) >= self.params['min_similarity']):
            yield (t['name'], (ngram['ngram'], r, peak, trough))

   def reduce_open_output(self):
      # output is opened in reduce()
      pass

   def reduce(self, target_series_name, matches):
      # Pretty much the only "real" work here is sorting matches.
      def abs1(x):
         return abs(x[1])  # element 1 is the correlation
      # Output here is kind of awkward. We want one TSV output file per XLS
      # input file, which corresponds to one key, so we re-open the output
      # stream each time reduce() is called. We also have to no-op
      # reduce_open_output() above, which seems strange to me.
      self.outfp = tsv_glue.Writer('%s/%s.tsv' % (self.outdir,
                                                  target_series_name),
                                   clobber=True, buffering=base.OUTPUT_BUFSIZE)
      for m in sorted(matches, key=abs1, reverse=True):
         yield m


class Tweet_Job(base.TSV_Input_Job, Build_Job):

   def __init__(self, params):
      base.Job.__init__(self, params)
      self.tzer = tok.unicode_props.UP_Tiny(self.params['n'])

   def map(self, fields):
      # WARNING: make sure field indices match any file format changes
      date = fields[1][:10]  # first 10 characters of ISO 8601 string is date
      for token in self.tzer.tokenize(fields[2]):  # tweet text
         yield (token, (date, 1))

class Wikimedia_Job(Build_Job):

   def map(self, fields):
      date = int(fields[0])  # Gregorian ordinal
      project = fields[1]
      # We don't decode the article name (which uses percent-encoding to
      # encode bytes and then some encoding to encode high characters) because
      # (a) it saves significant time and (b) there are apparently non-UTF-8
      # encodings in use. I believe the latter is selected by the browser.
      #
      # An artifact of (b) is that article counts can be split. For example,
      # the Russian article Люди Икс (i.e., the X-Men comic series) can be
      # accessed at both of the following URLs:
      #
      #   (UTF-8)        http://ru.wikipedia.org/wiki/%D0%9B%D1%8E%D0%B4%D0%B8_%D0%98%D0%BA%D1%81
      #   (Windows-1251) http://ru.wikipedia.org/wiki/%CB%FE%E4%E8_%C8%EA%F1
      #
      # Other encodings (e.g., ISO 8859-5: %BB%EE%D4%D8_%B8%DA%E1 and KOI8-R,
      # %EC%C0%C4%C9_%E9%CB%D3) do not work. Figuring out this mess is
      # something I'm not very interested in.
      #
      # We do, however, normalize spaces into underscores. I believe this may
      # be incomplete (see issue #77).
      article = fields[2].replace('%20', '_')
      count = int(fields[3])
      #print >>sys.stderr, type(project + ' ' + article)
      yield (project + ' ' + article, (date, count))

   def map_open_input(self):
      # Input is space-separated lines which are byte sequences, not UTF-8
      # encoded text. We can coerce tsv_glue.Reader to read this.
      self.infp = tsv_glue.Reader(sys.stdin.fileno(), separator=' ', mode='b')

   def map_write(self, key, value):
      'Treat key and value as a stream of bytes rather than Unicode objects.'
      self.outfp.write(key)
      self.outfp.write('\t')
      self.outfp.write(base.encode(value))
      self.outfp.write('\n')
