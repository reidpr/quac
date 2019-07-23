# Evaluation functions takes two Series: (1) model predicted incidence and (2)
# "true" incidence from reference data. The latter should be trimmed to the
# period you want to compare, and Pandas will use the indexes to compare only
# the part of the prediction that overlaps.

import numpy as np


def hit_rate(estimate, refdata):
   # This metric compares each pair of data points with the succeeding pair.
   # If both increased, both decreased, or both stayed the same, that's a hit;
   # otherwise, it's a miss. Hit rate is the number of hits divided by the
   # number of comparisons (weeks – 1).
   (e, r) = estimate.align(refdata, join="inner")
   return sum((   e.iloc[i] <  e.iloc[i+1] and r.iloc[i] <  r.iloc[i+1]
               or e.iloc[i] == e.iloc[i+1] and r.iloc[i] == r.iloc[i+1]
               or e.iloc[i] >  e.iloc[i+1] and r.iloc[i] >  r.iloc[i+1])
              for i in range(len(e) - 1)) / (len(e) - 1)

def peak_find(estimate, ref):
   # Find peaks. Parameters:
   #
   #   * Model estimate: Series
   #   * Reference data: Series
   #
   # Returns tuple with elements:
   #
   #   1. index of estimate peak week (integer) into estimate Series
   #   2. value of estimate peak week (real)
   #   3. index of reference peak week (integer) into estimate Series
   #   4. value of reference peak week (real)
   #   5. reference Series index offset (integer); i.e., subtract this from
   #      item 3 to get the index into the reference Series
   (e, r) = estimate.align(ref, join='inner')
   assert (r.equals(ref))
   i = e.index.get_loc(e.idxmax())
   j = r.index.get_loc(r.idxmax())
   delta_i = estimate.index.get_loc(r.index[0])
   return (i + delta_i, e.iloc[i], j + delta_i, r.iloc[j], delta_i)

def peak_intensity(estimate, ref):
   # Return difference in peak intensity e. Interpretation:
   #
   #   e = 0 : estimate equals reference peak
   #   e > 0 : estimate exceeds reference peak (overestimate)
   #   e < 0 : estimate less than reference peak (underestimate)
   (_, epeak, _, rpeak, _) = peak_find(estimate, ref)
   return (epeak - rpeak)

def peak_intensity_abs(estimate, ref):
   return abs(peak_intensity(estimate, ref))

def peak_timing(estimate, ref):
   # Return error e in peak timing. Interpretation:
   #
   #   e = 0 : estimate equals reference peak
   #   e > 0 : estimate follows reference peak (overestimate)
   #   e < 0 : estimate precedes reference peak (underestimate)
   (i, _, j, _, _) = peak_find(estimate, ref)
   return (i - j)

def peak_timing_abs(estimate, ref):
   return abs(peak_timing(estimate, ref))

def r2(estimate, refdata):
   return refdata.corr(estimate)**2

def rmse(estimate, refdata):
   # Note that Scikit-Learn has an MSE function,
   # sklearn.metrics.mean_squared_error(), but since it's a simple
   # calculation, we do it manually to avoid the import.
   (e, r) = estimate.align(refdata, join="inner")
   return np.sqrt(((e - r)**2).sum() / len(e))
