'''
Time series forecasting helper stuff.

These tests are mostly about demonstrating Pandas behavior, since it's not
always obvious how things work.

Correlation of period series:

  >>> index = pd.period_range('2015-02-01', freq='W-SAT', periods=6)
  >>> a = pd.Series([1,1,np.nan,2,3,  4], index=index)
  >>> b = pd.Series([2,2,   2.0,3,4,  5], index=index)
  >>> c = pd.Series([3,3,   4.0,5,6,999], index=index)
  >>> index
  PeriodIndex(['2015-02-01/2015-02-07', '2015-02-08/2015-02-14',
               '2015-02-15/2015-02-21', '2015-02-22/2015-02-28',
               '2015-03-01/2015-03-07', '2015-03-08/2015-03-14'],
              dtype='int64', freq='W-SAT')
  >>> a
  2015-02-01/2015-02-07     1
  2015-02-08/2015-02-14     1
  2015-02-15/2015-02-21   NaN
  2015-02-22/2015-02-28     2
  2015-03-01/2015-03-07     3
  2015-03-08/2015-03-14     4
  Freq: W-SAT, dtype: float64
  >>> b
  2015-02-01/2015-02-07    2
  2015-02-08/2015-02-14    2
  2015-02-15/2015-02-21    2
  2015-02-22/2015-02-28    3
  2015-03-01/2015-03-07    4
  2015-03-08/2015-03-14    5
  Freq: W-SAT, dtype: float64
  >>> c
  2015-02-01/2015-02-07      3
  2015-02-08/2015-02-14      3
  2015-02-15/2015-02-21      4
  2015-02-22/2015-02-28      5
  2015-03-01/2015-03-07      6
  2015-03-08/2015-03-14    999
  Freq: W-SAT, dtype: float64
  >>> a.corr(b)
  1.0
  >>> a.corr(c)
  0.773...

There are two ways to time-shift a Series.In both cases, this is easy to do by
an integer number of time periods (intervals such as P4W are not supported).
First, one can shift the index:

  >>> ash = a.tshift(-1)
  >>> ash
  2015-01-25/2015-01-31     1
  2015-02-01/2015-02-07     1
  2015-02-08/2015-02-14   NaN
  2015-02-15/2015-02-21     2
  2015-02-22/2015-02-28     3
  2015-03-01/2015-03-07     4
  Freq: W-SAT, dtype: float64

Because Pandas aligns the data based on the index, ash no longer correlates
with b but does with c.

  >>> ash.corr(b)
  0.943...
  >>> ash.corr(c)
  1.0

The second way is to shift the data; this introduces NaNs:

  >>> ash = a.shift(-1)
  >>> ash
  2015-02-01/2015-02-07     1
  2015-02-08/2015-02-14   NaN
  2015-02-15/2015-02-21     2
  2015-02-22/2015-02-28     3
  2015-03-01/2015-03-07     4
  2015-03-08/2015-03-14   NaN
  Freq: W-SAT, dtype: float64

Due to the data alignment, correlations don't change:

  >>> ash.corr(b)
  0.943...
  >>> ash.corr(c)
  1.0

Time series of different length are also properly dealt with:

  >>> ctr = c.iloc[2:5]
  >>> ctr
  2015-02-15/2015-02-21    4
  2015-02-22/2015-02-28    5
  2015-03-01/2015-03-07    6
  Freq: W-SAT, dtype: float64
  >>> ash.corr(ctr)
  1.0

Time cost. Some brief experiments suggest:

  - resampling takes about 2ms
  - time shifting and slicing take 100-500µs
  - this does not include garbage collection
'''

from pprint import pprint

import isodate
import numpy as np
import pandas as pd
import sklearn as sk
import sklearn.linear_model  # not imported by default

import testable
import timeseries
import u


class Context(object):

   '''Parameters for a model.

        >>> truth = pd.DataFrame({ 'us+lycanthropy': np.arange(12.0) },
        ...                      pd.period_range('2015-01-01', freq='W-SAT',
        ...                                      periods=12))
        >>> truth
                               us+lycanthropy
        2014-12-28/2015-01-03               0
        2015-01-04/2015-01-10               1
        2015-01-11/2015-01-17               2
        2015-01-18/2015-01-24               3
        2015-01-25/2015-01-31               4
        2015-02-01/2015-02-07               5
        2015-02-08/2015-02-14               6
        2015-02-15/2015-02-21               7
        2015-02-22/2015-02-28               8
        2015-03-01/2015-03-07               9
        2015-03-08/2015-03-14              10
        2015-03-15/2015-03-21              11
        >>> hits = pd.Series([-1.0,-1,0,1,2,3,5,5,6,7,8,9],
        ...                  pd.period_range('2015-01-01', freq='W-SAT',
        ...                                  periods=12))
        >>> hits
        2014-12-28/2015-01-03   -1
        2015-01-04/2015-01-10   -1
        2015-01-11/2015-01-17    0
        2015-01-18/2015-01-24    1
        2015-01-25/2015-01-31    2
        2015-02-01/2015-02-07    3
        2015-02-08/2015-02-14    5
        2015-02-15/2015-02-21    5
        2015-02-22/2015-02-28    6
        2015-03-01/2015-03-07    7
        2015-03-08/2015-03-14    8
        2015-03-15/2015-03-21    9
        Freq: W-SAT, dtype: float64

      Nowcasting model with 4-week training period.

        >>> n = Context(truth, 'us+lycanthropy', 4, 0, 7)
        >>> n
        Cx(us+lycanthropy, 4, 0, 7:2015-02-15)
        >>> n.truth
        2015-01-18/2015-01-24    3
        2015-01-25/2015-01-31    4
        2015-02-01/2015-02-07    5
        2015-02-08/2015-02-14    6
        Freq: W-SAT, Name: us+lycanthropy, dtype: float64
        >>> tr = n.alignshift(hits)
        >>> tr
        2015-01-18/2015-01-24    1
        2015-01-25/2015-01-31    2
        2015-02-01/2015-02-07    3
        2015-02-08/2015-02-14    5
        Freq: W-SAT, dtype: float64
        >>> n.corr(tr)
        0.982...

      2-week forecasting model with 4-week training period.

        >>> f = Context(truth, 'us+lycanthropy', 4, 2, 7)
        >>> f
        Cx(us+lycanthropy, 4, 2, 7:2015-02-15)
        >>> f.truth
        2015-01-18/2015-01-24    3
        2015-01-25/2015-01-31    4
        2015-02-01/2015-02-07    5
        2015-02-08/2015-02-14    6
        Freq: W-SAT, Name: us+lycanthropy, dtype: float64
        >>> tr = f.alignshift(hits)
        >>> tr
        2015-01-18/2015-01-24   -1
        2015-01-25/2015-01-31    0
        2015-02-01/2015-02-07    1
        2015-02-08/2015-02-14    2
        Freq: W-SAT, dtype: float64
        >>> f.corr(tr)
        1.0

      Fitting and evaluating a DataFrame:

        >>> d = { 'a': [0, 0, 1, 2, 3, 4, 5,  6,  7,   8,  9, 10],
        ...       'b': [4, 4, 5, 5, 6, 7, 8, 99, 99,  99, 99, 99],
        ...       'c': [3, 3, 4, 3, 2, 1, 0, -1, -2, -99, -4, -5] }
        >>> i = index=pd.period_range('2015-01-04', freq='W-SAT', periods=12)
        >>> df = pd.DataFrame(data=d, index=i)
        >>> df
                                a   b   c
        2015-01-04/2015-01-10   0   4   3
        2015-01-11/2015-01-17   0   4   3
        2015-01-18/2015-01-24   1   5   4
        2015-01-25/2015-01-31   2   5   3
        2015-02-01/2015-02-07   3   6   2
        2015-02-08/2015-02-14   4   7   1
        2015-02-15/2015-02-21   5   8   0
        2015-02-22/2015-02-28   6  99  -1
        2015-03-01/2015-03-07   7  99  -2
        2015-03-08/2015-03-14   8  99 -99
        2015-03-15/2015-03-21   9  99  -4
        2015-03-22/2015-03-28  10  99  -5
        >>> tr = n.alignshift(df)
        >>> tr
                               a  b  c
        2015-01-18/2015-01-24  1  5  4
        2015-01-25/2015-01-31  2  5  3
        2015-02-01/2015-02-07  3  6  2
        2015-02-08/2015-02-14  4  7  1
        >>> m = n.fit(tr)
        >>> [np.round(i, 2) for i in (m.intercept_, m.coef_)]
        [4.5, array([ 0.5,  0. , -0.5])]
        >>> np.round(m.predict(tr), 2)  # should be perfect on training data
        array([ 3.,  4.,  5.,  6.])
        >>> n.align_for_predict(df)
                                a   b   c
        2015-02-15/2015-02-21   5   8   0
        2015-02-22/2015-02-28   6  99  -1
        2015-03-01/2015-03-07   7  99  -2
        2015-03-08/2015-03-14   8  99 -99
        2015-03-15/2015-03-21   9  99  -4
        2015-03-22/2015-03-28  10  99  -5
        >>> pr = n.predict(m, df)
        >>> np.round(pr, 2)
        2015-02-15/2015-02-21     7
        2015-02-22/2015-02-28     8
        2015-03-01/2015-03-07     9
        2015-03-08/2015-03-14    58
        2015-03-15/2015-03-21    11
        2015-03-22/2015-03-28    12
        Freq: W-SAT, Name: us+lycanthropy$pred, dtype: float64
        >>> truth.loc['2015-02-15':]
                               us+lycanthropy
        2015-02-15/2015-02-21               7
        2015-02-22/2015-02-28               8
        2015-03-01/2015-03-07               9
        2015-03-08/2015-03-14              10
        2015-03-15/2015-03-21              11
        >>> np.round(n.error(pr, truth), 2)
        0     0
        1     0
        2     0
        3    48
        4     0
        dtype: float64

      Output for 2-week forecasting context.

        >>> tr = f.alignshift(df)
        >>> tr
                               a  b  c
        2015-01-18/2015-01-24  0  4  3
        2015-01-25/2015-01-31  0  4  3
        2015-02-01/2015-02-07  1  5  4
        2015-02-08/2015-02-14  2  5  3
        >>> m = f.fit(tr)
        >>> [np.round(i, 2) for i in (m.intercept_, m.coef_)]
        [1.5, array([ 0.99,  0.5 ,  0.  ])]
        >>> f.align_for_predict(df)
                               a   b   c
        2015-03-01/2015-03-07  5   8   0
        2015-03-08/2015-03-14  6  99  -1
        2015-03-15/2015-03-21  7  99  -2
        2015-03-22/2015-03-28  8  99 -99
        >>> pr = f.predict(m, df)
        >>> np.round(pr, 2)
        2015-03-01/2015-03-07    10.43
        2015-03-08/2015-03-14    56.69
        2015-03-15/2015-03-21    57.68
        2015-03-22/2015-03-28    58.21
        Freq: W-SAT, Name: us+lycanthropy$pred, dtype: float64
        >>> truth.loc['2015-03-01':]
                               us+lycanthropy
        2015-03-01/2015-03-07               9
        2015-03-08/2015-03-14              10
        2015-03-15/2015-03-21              11
        >>> np.round(f.error(pr, truth), 2)
        0     1.43
        1    46.69
        2    46.68
        dtype: float64'''

   def __init__(self, truth, outbreak, training, horizon, now):
      self.outbreak = outbreak
      self.training = training
      self.horizon = horizon
      self.now = now
      self.truth = truth[self.outbreak].iloc[self.now - self.training:self.now]

   def __eq__(self, other):
      return (   (self.outbreak,  self.training,  self.horizon,  self.now )
              == (other.outbreak, other.training, other.horizon, other.now))

   def __hash__(self):
      return hash((self.outbreak, self.training, self.horizon, self.now))

   def __ne__(self, other):
      return not self.__eq__(other)

   def __repr__(self):
      return 'Cx(%s, %d, %d, %d:%s)' % (self.outbreak, self.training,
                                        self.horizon, self.now,
                                        isodate.date_isoformat(self.now_date))

   @property
   def freq(self):
      return self.truth.index

   @property
   def now_date(self):
      return self.truth.index[-1].to_timestamp() + self.period_duration

   @property
   def horizon_duration(self):
      return self.period_duration * self.horizon

   @property
   def period_duration(self):
      # FIXME: This seems awkward and depends on a non-empty truth series, but
      # it works for now.
      return (  self.truth.index[1].to_timestamp()
              - self.truth.index[0].to_timestamp()).to_pytimedelta()

   @property
   def training_duration(self):
      return self.period_duration * self.training

   def align_for_predict(self, src):
      'Return src aligned for prediction.'
      return src.shift(self.horizon).loc[self.now_date+self.horizon_duration:]

   def alignshift(self, hits):
      """Return a copy of hits shifted and trimmed to match self.truth. hits
         must have the same frequency as self.truth."""
      return hits.shift(self.horizon, axis=0) \
                 .align(self.truth, axis=0, join='right')[0]

   def corr(self, data):
      return self.truth.corr(data)

   def error(self, preds, truth):
      '''Return error by prediction staleness.'''
      (p, t) = preds.align(truth[self.outbreak], join='inner')
      return (p - t).reset_index(drop=True)

   def fit(self, df):
      assert (    df.index[0] == self.truth.index[0]
              and df.index[-1] == self.truth.index[-1])
      # FIXME: These parameters seem troublesome. alpha=1, which is the
      # default, yields coefficients that are all zero in initial testing. So
      # for now, we'll use orginary least squares because that gets us working
      # models. Maybe what we want is ridge regression, since it seems we
      # don't care about coefficients being zero. Talk to Dave.
      #alg = sk.linear_model.LinearRegression()
      #alg = sk.linear_model.ElasticNet(alpha=1, l1_ratio=0.5)
      alg = sk.linear_model.RidgeCV(np.logspace(-5, 1, 20))
      return alg.fit(df, self.truth)

   def predict(self, m, src):
      '''Return incidence predictions based on the data in src, from self.now
         until the end of src. Order of columns in src must match what was
         fitted earlier to generate m.'''
      src = self.align_for_predict(src)
      return pd.Series(m.predict(src), index=src.index,
                       name=self.truth.name + '$pred')

   def time_eq(self, other):
      return (other is not None
              and    ( self.training,  self.horizon,  self.now )
                  == (other.training, other.horizon, other.now))


def nows(truth_len, train_len, test_horizon, stride):
   '''e.g.:

      >>> list(nows(2, 1, 0, 1))
      [1]
      >>> list(nows(5, 1, 0, 1))
      [1, 2, 3, 4]
      >>> list(nows(5, 2, 0, 1))
      [2, 3, 4]
      >>> list(nows(5, 2, 0, 2))
      [2, 4]
      >>> list(nows(5, 2, 1, 2))
      []
      >>> list(nows(53, 8, 4, 4))
      [12, 16, 20, 24, 28, 32, 36, 40, 44, 48]'''
   assert (truth_len >= 2)
   assert (train_len >= 1)
   assert (test_horizon >= 0)
   assert (stride >= 1)
   assert (train_len + test_horizon + 1 <= truth_len)  # need at least one now
   return (i for i in range(0, truth_len - test_horizon, stride)
           if i >= train_len + test_horizon)


def sin(start, interval, count, wavelength, phase):
   '''Return a Pandas period series containing a sine wave of amplitude 1.
      Parameters (see https://en.wikipedia.org/wiki/Sine_wave):

        start       starting timestamp (anything Pandas will accept)
        interval    period interval code
        count       number of periods to include
        wavelength  wavelength in seconds
        phase       phase in seconds (positive = advance, negative = delay)

      For example:

        >>> sin('2015-01-01', 'H', 9, 8*60*60, 0)
        2015-01-01 00:00    0.000000e+00
        2015-01-01 01:00    7.071068e-01
        2015-01-01 02:00    1.000000e+00
        2015-01-01 03:00    7.071068e-01
        2015-01-01 04:00    1.224647e-16
        2015-01-01 05:00   -7.071068e-01
        2015-01-01 06:00   -1.000000e+00
        2015-01-01 07:00   -7.071068e-01
        2015-01-01 08:00   -2.449294e-16
        Freq: H, dtype: float64

        >>> sin('2015-01-01', 'H', 9, 8*60*60, 2*60*60)  # i.e., cos()
        2015-01-01 00:00    1.000000e+00
        2015-01-01 01:00    7.071068e-01
        2015-01-01 02:00    1.224647e-16
        2015-01-01 03:00   -7.071068e-01
        2015-01-01 04:00   -1.000000e+00
        2015-01-01 05:00   -7.071068e-01
        2015-01-01 06:00   -2.449294e-16
        2015-01-01 07:00    7.071068e-01
        2015-01-01 08:00    1.000000e+00
        Freq: H, dtype: float64

      We can use this to set up a dummy fitting problem. We'll use a truth of
      365-day wavelength wave with zero phase offset, generate a few time
      series with the same wavelengths and different phases, and create a
      model which should be 100% correct within floating point error.

        >>> SY = 365*86400  # approx seconds per year; ignore leap years/seconds
        >>> truth = sin('2010-07-04', 'W-SAT', 104, SY, 0)
        >>> truth.name = 'test'
        >>> truth_df = pd.DataFrame(truth)
        >>> truth_df.head()
                                   test
        2010-07-04/2010-07-10  0.000000
        2010-07-11/2010-07-17  0.120208
        2010-07-18/2010-07-24  0.238673
        2010-07-25/2010-07-31  0.353676
        2010-08-01/2010-08-07  0.463550
        >>> truth_df.tail()
                                   test
        2012-05-27/2012-06-02 -0.594727
        2012-06-03/2012-06-09 -0.493776
        2012-06-10/2012-06-16 -0.385663
        2012-06-17/2012-06-23 -0.271958
        2012-06-24/2012-06-30 -0.154309

        >>> reqs_df = pd.DataFrame(
        ...    { 'a': sin('2010-07-04', 'W-SAT', 104, SY, 0),
        ...      'b': sin('2010-07-04', 'W-SAT', 104, SY, 10 * 7 * 86400),
        ...      'c': sin('2010-07-04', 'W-SAT', 104, SY, 13 * 7 * 86400),
        ...      'd': sin('2010-07-04', 'W-SAT', 104, SY, 23 * 7 * 86400) })
        >>> reqs_df.head()
                                      a         b         c         d
        2010-07-04/2010-07-10  0.000000  0.933837  0.999991  0.361714
        2010-07-11/2010-07-17  0.120208  0.970064  0.993257  0.247022
        2010-07-18/2010-07-24  0.238673  0.992222  0.972118  0.128748
        2010-07-25/2010-07-31  0.353676  0.999991  0.936881  0.008607
        2010-08-01/2010-08-07  0.463550  0.993257  0.888057 -0.111659

      Nowcast:

        >>> ctx_n = Context(truth_df, 'test', 52, 0, 62)
        >>> ctx_n
        Cx(test, 52, 0, 62:2011-09-11)
        >>> train = ctx_n.alignshift(reqs_df)
        >>> train.head()
                                      a         b         c         d
        2010-09-12/2010-09-18  0.933837  0.668064  0.361714 -0.741222
        2010-09-19/2010-09-25  0.970064  0.573772  0.247022 -0.816538
        2010-09-26/2010-10-02  0.992222  0.471160  0.128748 -0.880012
        2010-10-03/2010-10-09  0.999991  0.361714  0.008607 -0.930724
        2010-10-10/2010-10-16  0.993257  0.247022 -0.111659 -0.967938
        >>> train.tail()
                                      a         b         c         d
        2011-08-07/2011-08-13  0.552435  0.976011  0.835925 -0.213521
        2011-08-14/2011-08-20  0.648630  0.942761  0.763889 -0.329408
        2011-08-21/2011-08-27  0.735417  0.895839  0.680773 -0.440519
        2011-08-28/2011-09-03  0.811539  0.835925  0.587785 -0.545240
        2011-09-04/2011-09-10  0.875892  0.763889  0.486273 -0.642055
        >>> np.round([ctx_n.corr(train[i]) for i in train.columns], 3)
        array([ 1.   ,  0.355,  0.002, -0.932])
        >>> m = ctx_n.fit(train)
        >>> np.abs(np.round(m.intercept_, 4))
        0.0
        >>> np.round(m.coef_, 4)
        array([ 0.5007,  0.1788,  0.0019, -0.4669])
        >>> pr = ctx_n.predict(m, reqs_df)
        >>> err = ctx_n.error(pr, truth_df)
        >>> np.round(np.sum(np.abs(err)), 4)
        0.0

      10-week forecast:

        >>> ctx_f = Context(truth_df, 'test', 52, 10, 62)
        >>> ctx_f
        Cx(test, 52, 10, 62:2011-09-11)
        >>> train = ctx_f.alignshift(reqs_df)
        >>> train.head()
                                      a         b         c         d
        2010-09-12/2010-09-18  0.000000  0.933837  0.999991  0.361714
        2010-09-19/2010-09-25  0.120208  0.970064  0.993257  0.247022
        2010-09-26/2010-10-02  0.238673  0.992222  0.972118  0.128748
        2010-10-03/2010-10-09  0.353676  0.999991  0.936881  0.008607
        2010-10-10/2010-10-16  0.463550  0.993257  0.888057 -0.111659
        >>> train.tail()
                                      a         b         c         d
        2011-08-07/2011-08-13 -0.580800  0.552435  0.811539  0.835925
        2011-08-14/2011-08-20 -0.478734  0.648630  0.875892  0.763889
        2011-08-21/2011-08-27 -0.369725  0.735417  0.927542  0.680773
        2011-08-28/2011-09-03 -0.255353  0.811539  0.965740  0.587785
        2011-09-04/2011-09-10 -0.137279  0.875892  0.989932  0.486273
        >>> np.round([ctx_f.corr(train[i]) for i in train.columns], 3)
        array([ 0.359,  1.   ,  0.935,  0.002])
        >>> m = ctx_f.fit(train)
        >>> np.abs(np.round(m.intercept_, 4))
        0.0
        >>> np.round(m.coef_, 4)
        array([ 0.1788,  0.4993,  0.4669,  0.0019])
        >>> pr = ctx_f.predict(m, reqs_df)
        >>> pr.head()
        2011-11-20/2011-11-26    0.680773
        2011-11-27/2011-12-03    0.587785
        2011-12-04/2011-12-10    0.486273
        2011-12-11/2011-12-17    0.377708
        2011-12-18/2011-12-24    0.263665
        Freq: W-SAT, Name: test$pred, dtype: float64
        >>> err = ctx_f.error(pr, truth_df)
        >>> np.round(np.sum(np.abs(err)), 4)
        0.0

 '''
   index = pd.period_range(start, freq=interval, periods=count)
   values = np.array([(  i.to_timestamp()
                       - index[0].to_timestamp()).total_seconds()
                      for i in index])
   values /= wavelength / (2 * np.pi)
   values += (phase / wavelength) * 2 * np.pi
   values = np.sin(values)
   s = pd.Series(values, index=index)
   return s

# Since this stuff is experimental, we don't make the standard test suite
# depend on it.
#
# Test-Depends: manual
testable.register()
