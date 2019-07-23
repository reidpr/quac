import abc

import numpy as np
import pandas as pd


## Noise functions

# All of these take a template index.

def normal(index, name="normal"):
   return pd.Series(np.random.normal(scale=1, size=len(index)),
                    index, name=name)

def constant(index, name="constant"):
   return pd.Series(np.ones(len(index)), index, name=name)

def pulse(index, pulses, name="pulse"):
   # This is the "Oprah Effect". Arguments:
   #
   #   1. index
   #   2. pulses; sequence of (start, interval count) tuples
   #
   data = np.zeros(len(index))
   for (start, len_) in pulses:
      assert (len_ >= 1)
      i = index.get_loc(start)
      data[i:i+len_] = 1.0
   return pd.Series(data, index, name=name)

def linear(index, start=None, end=None, name="linear"):
   # Start at 0; drift up to 1 starting at `start` and completing at `end`,
   # both inclusive. If either argument is omitted, then use the first/last
   # element respectively.
   start = 0 if (start is None) else index.get_loc(start)
   end = (len(index) - 1) if (end is None) else index.get_loc(end)
   data = np.zeros(len(index))
   data[start:end+1] = np.linspace(0, 1, end-start+1)
   data[end:] = 1.0
   return pd.Series(data, index, name=name)

def sin(index, cycle_ct, phase=0, end=None, name="sine"):
   # Sine wave.
   #
   #   1. index
   #   2. number of cycles
   #   3. starting phase in rotations (e.g. 0=sine, 0.5=cosine)
   #   4. last week in cycle; one after (default: last week in index)
   #
   phase = phase * 2 * np.pi
   end = (len(index) - 1) if (end is None) else index.get_loc(end)
   x = np.linspace(phase, cycle_ct * 2 * np.pi + phase, len(index))
   data = pd.Series(np.sin(x), index, name=name) / 2 + 0.5
   data.iloc[end+1:] = 1
   return data


## Deceptiveness computation

def deceptiveness(wu, wr, ws):
   # Return a feature's deceptiveness. Note that the computation here is
   # different from the flow paper.
   #
   #   * Inputs: signal weight, systematic noise weight, random noise weight
   #             These scalars must sum to 1.
   #
   #   * Output: tuple:
   #               total deceptiveness,
   #               systematic deceptiveness,
   #               random deceptiveness
   #
   assert np.isclose(wu + wr + ws, 1)
   # Use min() in case the sum is slightly greater than 1 due to rounding
   # issues. Deceptiveness must be strictly <= 1.
   return (min(ws + wr, 1), min(wr, 1), min(ws, 1))


## Add noise to a Series

def decept_draw(noise, s):
   assert 0 <= noise <= 1
   shuffled = s.sample(frac=1)
   shuffled.index = s.index
   assert set(s.index) == set(shuffled.index)  # same index
   assert sorted(s) == sorted(shuffled)        # same values
   assert not s.equals(shuffled)               # different order
   return (1-noise) * s + noise * shuffled


## Synthetic feature generator classes

class Feature_Maker(abc.ABC):

   __slots__ = ("signal",      # Series
                "sys_bases")   # DataFrame; columns=bases, rows=weeks

   def __init__(self, signal, sys_bases):
      self.signal = signal / signal.max()
      self.sys_bases = sys_bases

   def feature_draw(self, w=None, **kwargs):
      # Returns big ugly tuple:
      #   ( feature : series,
      #     signal : series,
      #     systematic noise : series,
      #     random noise : series,
      #     total deceptiveness : float,
      #     random deceptiveness : float,
      #     systematic deceptiveness : float,
      #     weights : array )
      # All series have the same index (weeks) as self.signal.
      if (w is None):
         w = self.weights_draw(**kwargs)
      u = w[0]  * self.signal
      r = w[1]  * normal(self.signal.index)
      s = w[2:] @ self.sys_bases.T
      x = (u + r + s).clip(0)
      u.name = "signal"
      r.name = "random noise"
      s = pd.Series(s, name="systematic noise", index=self.signal.index)
      x.name = "feature"
      assert (x.index.equals(self.signal.index))
      (g, gr, gs) = deceptiveness(w[0], w[1], w[2:].sum())
      return (x, u, s, r, g, gr, gs, w)

   def features_draw(self, count=None, **kwargs):
      # Returns tuple:
      #   ( features : dataframe: cols: feature id, rows: weeks,
      #     deceptiveness : series: index: feature id,
      #     raw return values from feature_draw() : list )
      raw = self.features_draw_raw(count=count, **kwargs)
      for (i, r) in enumerate(raw):
         r[0].name = i
      features = pd.concat((i[0] for i in raw), axis=1)
      decept = pd.Series((i[6] for i in raw), name="systematic deceptiveness")
      assert (features.columns.equals(decept.index))
      return (features, decept, raw)

   def features_draw_raw(self, count, **kwargs):
      return [self.feature_draw(**kwargs) for i in range(count)]

   @abc.abstractmethod
   def weights_draw(self, **kwargs):
      ## the weights in the following order:
      # signal
      # random
      # syst-oprah-annual
      # syst-oraph-fore
      # syst-oprah-late
      # syst-drift-steady
      # syst-drift-late
      # syst-cycle-inseason
      # syst-cycle-offseason)
      ...


class Feature_Maker_Dirichlet(Feature_Maker):

   def weights_draw(self, alpha_srs, alpha_odc):
      ## sample signal, random, systematic weights
      srs_wt   = np.random.dirichlet(alpha_srs, 1)

      ## sample oprah, drift, cyclic weights
      odc_wt   = np.random.dirichlet(alpha_odc, 1)

      ## sample one of three oprah effects
      oprah = np.zeros(3)
      oprah[np.random.choice([0,1,2], size=1)] = 1

      ## sample one of two drifts
      drift = np.zeros(2)
      drift[np.random.choice([0,1], size=1)] = 1

      ## sample one of two cycle
      cyclic = np.zeros(2)
      cyclic[np.random.choice([0,1], size=1)] = 1

      ## make final weight vector
      ## signal weight
      weights = np.zeros(9)
      weights[0] = srs_wt[0][0]

      ## random weight
      weights[1] = srs_wt[0][1]

      ## oprah weights
      weights[2] = srs_wt[0][2] * odc_wt[0][0] * oprah[0]
      weights[3] = srs_wt[0][2] * odc_wt[0][0] * oprah[1]
      weights[4] = srs_wt[0][2] * odc_wt[0][0] * oprah[2]

      ## drift weights
      weights[5] = srs_wt[0][2] * odc_wt[0][1] * drift[0]
      weights[6] = srs_wt[0][2] * odc_wt[0][1] * drift[1]

      ## cyclic weights
      weights[7] = srs_wt[0][2] * odc_wt[0][2] * cyclic[0]
      weights[8] = srs_wt[0][2] * odc_wt[0][2] * cyclic[1]

      return(weights)


class Feature_Maker_Enumerated(Feature_Maker):

   def features_draw_raw(self, count, *, ss_step_ct, r_noise):
      # ss_step_ct: number of steps between 100% signal and 100% noise
      # r_noise: list of random noise levels
      assert (count is None)
      raw = list()
      # relative weight of signal and systematic noise
      thetas = np.linspace(0, np.pi, ss_step_ct)
      ws_sig = (np.cos(thetas) + 1) / 2
      ws_sys = 1 - ws_sig
      # walk through random noise levels and different systematic noise bases
      for i in range(ss_step_ct):
         for w_rnd in r_noise:
            for j in range(len(self.sys_bases.columns)):
               # only need one copy of zero systematic noise
               if (np.isclose(ws_sys[i], 0) and j > 0):
                  continue
               # deliberately fool ridge: skip if low random and low systematic
               if (ws_sys[i] <= 0.40 and w_rnd <= 0.12):
                  continue
               weights = np.zeros(9)
               weights[0] =   ws_sig[i] * (1 - w_rnd)  # signal
               weights[1] =   w_rnd                    # random
               weights[j+2] = ws_sys[i] * (1 - w_rnd)  # systematic
               raw.append(self.feature_draw((weights)))
      return raw

   def weights_draw(self):
      raise NotImplementedError("Feature_Maker_Enumerated doesn't draw weights")
