import datetime
import heapq
from pprint import pprint
import os.path
import sys
import time

import isodate
import numpy as np
import pandas as pd
import pyspark
import xlrd

# This voodoo makes the QUAC modules available in the driver program, because
# we don't want to pass hundreds of files with --py-files or zip them up on
# every run. Modules installed in the virtualenv work because Spark uses the
# right interpreter. Below, we use different voodoo to make the modules
# available in the workers.
QUACLIB = os.path.abspath(os.path.dirname(__file__) + '/../../lib')
sys.path.insert(0, QUACLIB)

import forecast
import timeseries
import u

### Globals ###

# Configuration and log; these are not used in workers.
c = u.c
l = u.l

# Raw arguments
args = None

# Ground truth data
truth = None

# Test parameters
tests = None


### Setup ###

ap = u.ArgumentParser()
gr = ap.default_group
gr.add_argument('tspath',
                metavar='TSPATH',
                help='path to time series dataset')
gr.add_argument('truth',
                metavar='TRUTHXLS',
                help='path to ground truth Excel file')
gr.add_argument('outdir',
                metavar='OUTDIR',
                help='directory for output')
gr.add_argument('--candidates',
                metavar='N',
                type=int,
                default=100,
                help='number of candidate articles for regression')
gr.add_argument('--freq',
                required=True,
                metavar='F',
                help='use truth with frequency F')
gr.add_argument('--horizon',
                nargs='+',
                required=True,
                metavar='N',
                type=int,
                help='forecast horizons to test (number of intervals)')
gr.add_argument('--limit',
                metavar='N',
                type=int,
                default=sys.maxsize,
                help='stop after this many time series per worker')
gr.add_argument('--profile',
                action='store_true',
                help='run under the Spark profiler')
gr.add_argument('--teststride',
                required=True,
                type=int,
                metavar='N',
                help='number of intervals between model builds')
gr.add_argument('--training',
                nargs='+',
                required=True,
                metavar='N',
                type=int,
                help='training periods to test (number of intervals)')
gr.add_argument('--shards',
                metavar='N',
                type=int,
                help='use this many shards, instead of all in dataset')
gr.add_argument('--sin',
                action='store_true',
                help='use sine waves instead of real input data')


### Main ###

def main():
   l.info('starting')
   args_clean()
   # set up Spark
   conf = pyspark.SparkConf()
   conf.setExecutorEnv('PYTHONPATH', QUACLIB)
   if (args.profile):
      conf.set('spark.python.profile', 'true')
   sc = pyspark.SparkContext(conf=conf)
   global args_b
   args_b = sc.broadcast(args)
   # load ground truth data
   global truth
   truth = truth_load()
   l.info('found truth with %d outbreaks' % len(truth.columns))
   global truth_b
   truth_b = sc.broadcast(truth)
   # find dataset
   shard_ct = shards_count()
   l.info('found dataset with %d shards' % shard_ct)
   if (args.shards is not None):
      shard_ct = args.shards
   l.info('will process %d shards' % shard_ct)
   # figure out what tests to do
   global tests
   tests = tests_enumerate()
   l.info('planning %d tests' % len(tests))
   global tests_b
   tests_b = sc.broadcast(tests)
   # some timing accumulators
   global article_ct
   article_ct = sc.accumulator(0)
   global eval_elapsed
   eval_elapsed = sc.accumulator(0)
   # let's go
   l.info('starting computation')

   # 1. Distribute shard indexes
   #
   shards = sc.parallelize(range(shard_ct), shard_ct)

   # 2. Find candidate articles
   #
   # 2a. Find top candidates within each shard for each context
   #
   #     key: Context
   #     val: Priority_Queue:
   #             pri:  r [correlation with ground truth on training data]
   #             val:  (Series [complete time series, .name is URL],
   #                    Series [shifted/truncated training data, .name is URL])
   cands = shards.flatMap(candidates_read)

   # 2b. Find global top candidates for each context
   #
   #     (form same as above)
   cands = cands.reduceByKey(candidates_merge)
   cands.cache()

   # 2c. Dump top candidate summaries
   #
   #     articles and correlations for each context
   #       key: outbreak
   #       val: dict:
   #              key: (training duration (timedelta),
   #                    forecast horizon (timedelta),
   #                    now (datetime))
   #              val: articles (ordered list of (URL, r))
   #l.info('dumping candidate summaries')
   #summs = cands.map(candidate_summarize) \
   #             .reduceByKey(u.dicts_merge)
   #summs.foreach(pickle_dump('r'))

   # 3. Build models
   #
   # 3a. Build a model for each context
   #
   #       key: Context
   #       val: (sk.LinearModel [fitted model],
   #             DataFrame [full candidate time series, URL columns],
   #             DataFrame [training candidate time series, URL columns])
   #
   #     Order of coefficients in model and DataFrame are the same.
   models = cands.map(model_build)
   models.cache()

   # 3b. Dump models and article data for each context. These dumps are
   #     self-contained enough to be loaded in a Python interpreter that is
   #     not QUAC-aware. This should produce a few 10's of GiB of data.
   #
   #       key: outbreak
   #       val: { horizon:
   #              { training:
   #                { now:
   #                  { 'model':  sk.LinearModel [fitted model],
   #                    'data':   DataFrame [full data, URL columns],
   #                    'trdata': DataFrame [training data, URL columns] }}}}
   summs = models.map(model_summarize) \
                 .reduceByKey(u.dicts_merge)
   summs.foreach(pickle_dump('model'))

   # 4. Evaluate models
   #
   # 4a. Compute predicted values
   #
   #       key: Context
   #       val: Series [predicted incidence]
   #               index: period
   #               values: prediction)
   preds = models.map(model_predict)

   # 4b. Re-key results to put nows in value
   #
   #       key: (outbreak, training duration, forecast horizon)
   #       val: (now, Series [predicted incidence])
   preds = preds.map(lambda x: ((x[0].outbreak, x[0].training, x[0].horizon),
                                (x[0].now, x[1])))

   # 4c. Summarize results (~2K keys)
   #
   #       key: (outbreak, training duration, forecast horizon)
   #       val: (DataFrame [predicted incidence]:
   #               index: period
   #               columns: nows)
   preds = preds.groupByKey() \
                .map(model_result_summarize)

   # 4d. Gather results by outbreak (~20 keys, ~20MB/key)
   #
   #       key: outbreak
   #       val: dict:
   #              key: forecast horizon
   #              val: dict:
   #                     key: training duration
   #                     val: DataFrame [predicted incidence]
   #
   #       Note: we could also use a Panel4D for this, but I haven't put in
   #       the effort to wrap my head around it.
   preds = preds.map(lambda x: (x[0][0], { x[0][2]: { x[0][1]: x[1] } })) \
                .reduceByKey(u.dicts_merge)

   # 4e. Dump predictions
   #
   #       For each outbreak, dump a pickle file containing the dict above.
   #       These are then translated to TSV files for plotting in later steps.
   preds.foreach(pickle_dump('out'))

   # finish up
   eval_ct = article_ct.value * len(tests)
   l.info('evaluated: %d articles, %d contexts, %d total; %s (%.0f µs/eval)'
          % (article_ct.value, len(tests), eval_ct,
             u.fmt_seconds(eval_elapsed.value),
             eval_elapsed.value * 1e6 / eval_ct))
   l.info('done')
   try:
      sc.dump_profiles(args.outdir)
      #sc.show_profiles()
   except AttributeError:
      pass


### Computation functions ###

def candidate_summarize(kv):
   (ctx, pq) = kv
   articles = [ (full.name, r) for (r, (full, train)) in pq.items() ]
   articles.sort()
   return (ctx.outbreak, { (ctx.training_duration,
                            ctx.horizon_duration,
                            ctx.now_date): articles })

def candidates_merge(pq_a, pq_b):
   return pq_a.merge(pq_b)

def candidates_read(worker_i):
   start = time.time()
   cands = [(ctx, u.Priority_Queue(args_b.value.candidates))
            for ctx in tests_b.value]
   for (i, full) in enumerate(input_read(worker_i)):
      if (i >= args_b.value.limit):
         break
      # Replace NaNs with zero. This is for two reasons. First, later fitting
      # and evaluation does not work with NaNs present. Second, it avoid
      # small-sample problems when there is only modest real overlap between
      # the time series and the truth because there are a lot of NaNs.
      full.fillna(0, inplace=True)
      last_ctx = None
      for (ctx, pq) in cands:
         if (not ctx.time_eq(last_ctx)):
            trim = ctx.alignshift(full)
          # Ignore traffic chunks that are all zero (because the flat pattern
          # is unlikely to be real)
         if (np.count_nonzero(trim.values) > 0):
            pq.add(ctx.corr(trim), (full, trim))
         last_ctx = ctx
   cands = [i for i in cands if len(i[1]) > 0]
   article_ct.add(i + 1)
   eval_elapsed.add(time.time() - start)
   return cands

def input_read(worker_i):
   if (not args_b.value.sin):
      # real data
      ds = timeseries.Dataset_Pandas(args_b.value.tspath)
      for i in ds.fetch_all(worker_i, last_only=False, normalize=True,
                            resample=args_b.value.freq):
         yield i
      ds.close()
   else:
      # fake data
      any_truth = truth_b.value.iloc[:,0]
      start = any_truth.index[0].to_timestamp()
      freq = args_b.value.freq
      count = len(any_truth)
      for phase in range(52):
         s = forecast.sin(start, freq, count, 365 * 86400, phase * 7 * 86400)
         s.name = 'sin%d' % phase
         yield s

def model_build(kv):
   (ctx, pq) = kv
   (full, train) = zip(*pq.values())
   df_full = pd.concat(full, axis=1)
   df_train = pd.concat(train, axis=1)
   df_full.fillna(0, inplace=True)  # NaNs crash fitting and prediction
   df_train.fillna(0, inplace=True)
   m = ctx.fit(df_train)
   return (ctx, (m, df_full, df_train))

def model_predict(kv):
   (ctx, (m, src, _)) = kv
   return (ctx, ctx.predict(m, src))

def model_result_summarize(kv):
   ((outbreak, training, horizon), results) = kv
   ps = list()
   for (now, s) in results:
      s.name = now
      ps.append(s)
   # Use outer join for concatenation even though all the indexes should be
   # the same, so that errors are more obvious later.
   ps = pd.concat(sorted(ps, key=lambda x: x.name), axis=1, join='outer')
   return ((outbreak, training, horizon), ps)

def model_summarize(item):
   (ctx, (m, df_full, df_train)) = item
   return (ctx.outbreak, { ctx.horizon:
                           { ctx.training:
                             { ctx.now: { 'model':  m,
                                          'data':   df_full,
                                          'trdata': df_train }}}})

def pickle_dump(tag):
   def dump(kv):
      (name, data) = kv
      u.pickle_dump('%s/%s.%s' % (args_b.value.outdir, name, tag), data)
   return dump


### Additional functions ###

def args_clean():
   l.info('  input:        %s' % args.tspath)
   l.info('  output:       %s' % args.outdir)
   l.info('  candidates:   %s' % args.candidates)
   l.info('  test stride:  %s' % args.teststride)
   l.info('  frequency:    %s' % args.freq)
   l.info('  horizon:      %s' % ",".join('%d' % i for i in args.horizon))
   l.info('  training:     %s' % ",".join('%d' % i for i in args.training))


def tests_enumerate():
   'Return an iterable of possible contexts, given args and truth.'
   tests = list()
   truedata_ct = len(next(truth.items())[1])
   for tr in args.training:
      for ho in args.horizon:
         # Eenumerate every possible now with sufficient time before for the
         # training period and sufficient time after for at least one test.
         for i in forecast.nows(truedata_ct, tr, ho, args.teststride):
            for (obk, truedata) in truth.items():
               # Outbreaks in the inner loop to they can share trim and shift.
               assert (truedata_ct == len(truedata))
               tests.append(forecast.Context(truth_b.value, obk, tr, ho, i))
   return tests


def to_date(book, x):
   return datetime.datetime(*xlrd.xldate_as_tuple(x, book.datemode))


def truth_load():
   truth = dict()
   # We could use Pandas' Excel functions instead, to save a dependecy, but
   # this seems perhaps clearer? I may be wrong.
   book = xlrd.open_workbook(args.truth)
   for sheet in book.sheets():
      if (args.freq == sheet.name):
         headers = sheet.row_values(0)
         dates = sheet.col_values(0, start_rowx=1)
         date_start = to_date(book, dates[0])
         date_end = to_date(book, dates[-1])
         index = pd.period_range(date_start, periods=len(dates), freq=args.freq)
         # If this fails, make sure the dates fall on the week start days you
         # expect. For example, 2010-07-04 is a Sunday.
         assert (    date_start == index[0].to_timestamp(how='start')
                 and date_end == index[-1].to_timestamp(how='start'))
         for (i, context) in enumerate(headers[1:], start=1):
            if (len(context) == 0 or context[0] == '_'):
               # not a real data series, skip
               continue
            data = ((j if j != '' else np.nan)
                    for j in sheet.col_values(i, start_rowx=1))
            truth[context] = pd.Series(data, index)
         args.ts_start = index[0].to_timestamp(how='start')
         args.ts_end = (index[-1].to_timestamp(how='end')
                        + datetime.timedelta(days=1)
                        - datetime.timedelta(microseconds=1))
         l.info('  periods:      %d' % len(index))
         l.info('  start:        %s (%s)' % (args.ts_start,
                                             args.ts_start.strftime('%A')))
         l.info('  end:          %s (%s)' % (args.ts_end,
                                             args.ts_end.strftime('%A')))
         break
   df = pd.DataFrame(truth, index=index)
   u.pickle_dump('%s/truth' % args.outdir, df)
   return df


def shards_count():
   ds = timeseries.Dataset(args.tspath)
   ds.group_get(ds.fragment_tags[0])  # open a group to initialize hashmod
   ct = ds.hashmod
   ds.close()
   return ct


### Bootstrap ###

if (__name__ == '__main__'):
   args = u.parse_args(ap)
   u.configure(args.config)
   u.logging_init('expmt')
   main()
