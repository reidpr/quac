#!/usr/bin/env python3

import datetime
import heapq
import itertools
from pprint import pprint
import operator
import os.path
import re
import sys
import time

import isodate
import joblib as jl
import numpy as np
import pandas as pd

# This voodoo makes the QUAC modules available.
QUACLIB = os.path.abspath(os.path.dirname(__file__) + '/../../lib')
sys.path.insert(0, QUACLIB)

import forecast
import timeseries
import u


### Globals ###

# Configuration and log; these are not used in workers.
c = u.c
l = u.l

# Namespace for global variables
class Namespace(object): pass
g = Namespace()


### Constants ###

# Map disease/location to root articles.
#
# Languages from
# <http://stats.wikimedia.org/archive/squid_reports/2016-01/SquidReportPageViewsPerCountryBreakdown.htm>, accessed March 23, 2016
#
# Use top language only, because the second language is always English; how is
# that helpful?
#
#     %tot    ar    de    en    es    he    ru
#     ----   ----  ----  ----  ----  ----  ----
# co   0.5               10.6  88.6              es
# de   7.5         75.3  18.1               1.3  de
# il   0.5    3.4        32.4        54.1   6.4  he
# us   21.9              93.6   1.0              en
#
ROOTS = {

   #'co+chlamydia': ['es+Infecciones_por_clamidias'],  # no data
   'co+dengue':    ['es+Dengue'],
   'co+influenza': ['es+Gripe'],  # only 2014-01-05 through 2015-05-17
   'co+malaria':   ['es+Malaria'],
   'co+measles':   ['es+Sarampi%C3%B3n'],
   'co+pertussis': ['es+Tos_ferina'],  # "pertussis from graphics" column

   # Germany uses ISO 8601 weeks: https://survstat.rki.de/Docs/Attributes.pdf
   #'de+chlamydia': ['de+Chlamydiose'],  # no data
   'de+dengue':    ['de+Denguefieber'],
   'de+influenza': ['de+Influenza'],
   #'de+malaria':   ['de+Malaria'],  # no data
   'de+measles':   ['de+Masern'],
   'de+pertussis': ['de+Keuchhusten'],

   'il+chlamydia': ['he+%D7%9B%D7%9C%D7%9E%D7%99%D7%93%D7%99%D7%94'],
   'il+dengue':    ['he+%D7%A7%D7%93%D7%97%D7%AA_%D7%93%D7%A0%D7%92%D7%99'],
   #'il+influenza': ['he+%D7%A9%D7%A4%D7%A2%D7%AA'],  # wacky flus only
   'il+malaria':   ['he+%D7%9E%D7%9C%D7%A8%D7%99%D7%94'],
   'il+measles':   ['he+%D7%97%D7%A6%D7%91%D7%AA'],
   'il+pertussis': ['he+%D7%A9%D7%A2%D7%9C%D7%AA'],

   'us+chlamydia': ['en+Chlamydia_infection'],
   'us+dengue':    ['en+Dengue_fever'],
   'us+influenza': ['en+Influenza'],
   'us+malaria':   ['en+Malaria'],
   'us+measles':   ['en+Measles'],
   'us+pertussis': ['en+Pertussis'],

   # Special version of us+influenza with bunch of confounds.
   'xx+influenza': ['en+Influenza', 'en+Basketball', 'en+College_basketball'],
}

# Countries where NAN means zero.
ZEROABLE = { 'de', 'us', 'xx' }


### Setup ###

ap = u.ArgumentParser()
gr = ap.default_group

gr.add_argument('--in',
                metavar='DIR',
                required=True,
                help='input data directory')
gr.add_argument('--out',
                metavar='DIR',
                required=True,
                help='output directory')
gr.add_argument('--distance',
                required=True,
                metavar='N',
                type=int,
                help='maximum category distance')
gr.add_argument('--horizons',
                nargs='+',
                required=True,
                metavar='N',
                type=int,
                help='forecast horizons to test (number of intervals)')
gr.add_argument('--outbreaks',
                nargs='+',
                metavar='CODE',
                help='outbreaks to test (default: all non-xx)')
gr.add_argument('--profile',
                action='store_true',
                help='run under the Spark profiler')
gr.add_argument('--teststride',
                required=True,
                type=int,
                metavar='N',
                help='number of intervals between model builds')
gr.add_argument('--trainings',
                nargs='+',
                required=True,
                metavar='N',
                type=int,
                help='training periods to test (number of intervals)')


### Main ###

def main():

   l.info('starting')
   start_time = time.time()
   args_clean()
   g.args = args

   u.memory_use_log(level=l.info)
   l.info('loading input data')
   g.truth = truth_load()
   g.graph = graph_load()
   g.vectors = vectors_load()
   u.memory_use_log(level=l.info)

   g.tests = tests_enumerate()
   l.info('scheduled %d tests' % len(g.tests))

   l.info('saving input data')
   pickle_dump('input', None, g)

   with jl.Parallel(n_jobs=-1, verbose=5) as P:

      l.info('1. Building models')
      #
      # { Context: sk.LinearModel [fitted model] }
      models = { ctx: m for (ctx, m)
                 in zip(g.tests, P(jl.delayed(model_build)(t) for t in g.tests))
                 if m is not None }
      l.info('built %d models (%d at max iterations)'
             % (len(models), sum(not m.converged for (_, m) in models.items())))

      l.info('2. Dumping models')
      # These dumps are self-contained enough to be loaded in a Python
      # interpreter that is not QUAC-aware.
      #
      # { outbreak: { horizon: { training: { now: fitted model } } } }
      summs = u.defaultdict_recursive()
      for (ctx, m) in models.items():
         summs[ctx.outbreak][ctx.horizon][ctx.training][ctx.now] = m
      for (ob, ob_data) in summs.as_dict().items():
         pickle_dump(ob, 'model', ob_data)

      l.info('3. Evaluating models')
      # Evaluations run in ~0.15s (according to joblib), so it's not clear to
      # me that distributing the computation outweighs overhead.
      #
      # { Context: Series [predicted incidence]
      #              index: period
      #              values: prediction }
      preds = dict(model_predict(cm) for cm in models.items())

      l.info('4. Aggregating results')
      # Re-key so we can aggregate the nows
      #
      # [ ((outbreak, training, horizon),
      #    (now, Series [predicted incidence])), ... ]
      preds = sorted(((ctx.outbreak, ctx.training, ctx.horizon), (ctx.now, p))
                     for (ctx, p) in preds.items())
      # Aggregate into DataFrames.
      #
      # { (outbreak, training, horizon): DataFrame [predicted incidence]
      #                                    index: period
      #                                    columns: now }
      preds = { k: model_summarize(preds)
                for (k, preds)
                in itertools.groupby(preds, operator.itemgetter(0)) }

      l.info('5. Dumping results')
      # Gather by outbreak
      #
      # { outbreak: { horizon: { training: DataFrame [predicted incidence] } } }
      preds2 = u.defaultdict_recursive()
      for ((ob, tr, ho), df) in preds.items():
         preds2[ob][ho][tr] = df
      # For each outbreak, dump a pickle file containing the dict above. These
      # are then translated to TSV files for plotting in later steps.
      for (ob, ob_data) in preds2.as_dict().items():
         pickle_dump(ob, 'out', ob_data)

   l.info('done in %s' % u.fmt_seconds(time.time() - start_time))


### Computation functions ###

def model_build(ctx):
   tr = ctx.alignshift(g.vectors[ctx.outbreak])
   try:
      return ctx.fit(tr)
   except forecast.Degenerate_Fit_Error:
      return None

def model_predict(cm):
   (ctx, m) = cm
   return (ctx, ctx.predict(m, g.vectors[ctx.outbreak]))

def model_summarize(preds):
   def fix(ns):
      (now, s) = ns
      s.name = now
      return s
   preds = [fix(ns[1]) for ns in sorted(preds)]
   # All the prediction vectors must end on the same (last) period.
   assert all(preds[0].index[-1] == s.index[-1] for s in preds)
   df = pd.concat(preds, axis=1)
   return df

def pickle_dump(name, tag, data):
   if (tag is not None):
      tag = '.' + tag
   else:
      tag = ''
   u.pickle_dump('%s/%s,%d%s' % (args.out, name, args.distance, tag), data)


### Additional functions ###

def args_clean():
   l.info('  input:        %s' % args.in_)
   l.info('  output:       %s' % args.out)
   l.info('  outbreaks:    %s' % ('default'
                                  if args.outbreaks is None
                                  else ' '.join(args.outbreaks)))
   l.info('  test stride:  %s' % args.teststride)
   l.info('  distance:     %d' % args.distance)
   l.info('  horizons:     %s' % ' '.join('%d' % i for i in args.horizons))
   l.info('  trainings:    %s' % ' '.join('%d' % i for i in args.trainings))

def graph_load():
   g = u.pickle_load(args.in_ + '/articles/wiki-graph.pkl.gz')
   for root in g.keys():
      g[root] = { timeseries.name_url_canonicalize(url): dist
                  for (url, dist) in g[root].items() }
   return g

def relevant_p(outbreak, article, distance):
   '''Return True if article is linked to outbreak and within distance, False
      otherwise.'''
   for root in ROOTS[outbreak]:
      if (article in g.graph[root]
          and g.graph[root][article] <= distance):
         return True
   return False

def tests_enumerate():
   'Return a list of possible contexts.'
   tests = list()
   for (ob, ob_truth) in g.truth.items():
      for tr in args.trainings:
         for ho in args.horizons:
            for i in forecast.nows(len(ob_truth), tr, ho, args.teststride):
               tests.append(forecast.Context(ob_truth, ob, tr, ho, i,
                                             minfinite=0.8, minrows=8))
   return tests

def truth_load():
   def keep(ob):
      if (args.outbreaks is None):
         return True
      else:
         return True if ob in args.outbreaks else False
   x = pd.read_excel(args.in_ + '/truth.xlsx', sheetname=None, index_col=0)
   r = dict()
   for (freq, df) in x.items():
      start = df.index[0]
      df.index = df.index.to_period(freq)
      # make sure the dates started the periods
      assert (start == df.index[0].to_timestamp(how='start'))
      df = df.dropna(axis=1, how='all')
      df = df.select(keep, axis=1)
      l.info('  %s:' % freq)
      l.info('    outbreaks:  %s' % len(df.columns))
      l.info('    periods:    %d' % len(df.index))
      l.info('    first:      %s (%s)' % (df.index[0], start.strftime('%A')))
      l.info('    last:       %s' % (df.index[-1]))
      for ob in df.columns:
         r[ob] = df.loc[:,ob]
         if (ob[:2] in ZEROABLE):
            r[ob].fillna(0, inplace=True)
   return r

def vectors_load():
   # 1. Load Wikipedia access log vectors.
   freqs = { ts.index.freq: ts for ts in g.truth.values() }
   dfs = dict()
   for (freq, eg) in freqs.items():
      freq = freq.name
      dfs[freq] = pd.read_table(('%s/tsv/forecasting_%s.norm.tsv'
                                 % (args.in_, freq)),
                                index_col=0, parse_dates=0)
      dfs[freq].index = dfs[freq].index.to_period(freq)
      dfs[freq].rename(columns=lambda c: re.sub(r'\$norm$', '', c), inplace=True)
      # 2. Clean up any NANs. We interpolate anything in the middle and change
      # boundary NANs to zero. Note that the boundaries are fairly well
      # outside the study period, so that should have minimal effect.
      dfs[freq].interpolate(method='linear', axis=0, inplace=True)
      dfs[freq].fillna(0, inplace=True)
      # 3. Trim the DataFrames to the study period. This doesn't have any effect,
      # since we trim to each test later, but it saves memory.
      (dfs[freq], _) = dfs[freq].align(eg, axis=0, join='inner')
      assert (dfs[freq].index.equals(eg.index))
   # 4. Build a DataFrame for each disease. This duplicates some vectors, but
   # not enough to be a worry.
   vs = dict()
   for (ob, ts) in sorted(g.truth.items()):
      freq = ts.index.freq.name
      dist = args.distance
      vs[ob] = dfs[freq].select(lambda c: relevant_p(ob, c, dist), axis=1)
      l.info('  %-15s %3d articles' % (ob + ':', len(vs[ob].columns)))
   return vs


### Bootstrap ###

if (__name__ == '__main__'):
   args = u.parse_args(ap)
   args.in_ = getattr(args, 'in')  # foo.in is a syntax error
   u.configure(args.config)
   u.logging_init('expmt')
   main()
