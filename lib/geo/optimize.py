from collections import defaultdict
import hashlib
import time

from django.contrib.gis import geos
import numpy as np
import scipy.optimize as scopt
import sklearn.mixture as skmix

import multicore
import testable
import u

l = u.l


class Weight(object):
   '''Optimizes the token_weights of a gmm.Model to minimize error. Objective
      function to be minimized is:

        argmin_w \sum_i [ \sum_j (c_ij * s(m_j)) / \sum_j s(m_j) ]

      where c_ij is the cost incurred by model m_j on tweet i, and
      s(m_j) = 1 / (1 + e^{-w_j}) is the weight for token j.

      By passing w_j through logistic function, no (0,1) constraints on w_j
      needed.

      gmms_list ........ list of lists of gmms, one list per tweet

      errors_list ...... list of lists of errors, one list per tweet,
                         corresponding to each gmm in gmms_list

      This test compares the analytical and empirical gradient of the
      objective function. If the difference is small, we probably implemented
      func and func_deriv correctly.
      >>> import gmm
      >>> gmm.Token.parms_init({})
      >>> mp = geos.MultiPoint(geos.Point(1,2), geos.Point(3,4), srid=4326)
      >>> m1 = gmm.Geo_GMM.from_fit(mp, 1, 'a')
      >>> m2 = gmm.Geo_GMM.from_fit(mp, 2, 'b')
      >>> m3 = gmm.Geo_GMM.from_fit(mp, 1, 'c')
      >>> m = Weight([[m1, m2], [m2, m3], [m1, m3]],
      ...            [[100, 50], [50, 200], [80, 400]], identity_feature=True,
      ...            misc_feature=False)
      >>> scopt.check_grad(m.func, m.func_deriv,
      ...                  np.ones(len(m.all_gmms)) / len(m.all_gmms)) < 0.0001
      True
      >>> tok_weights = m.optimize()
      >>> tok_weights['b'] > tok_weights['a']
      True
      >>> tok_weights['b'] > tok_weights['c']
      True
      >>> m = Weight([[m1, m2], [m2, m3], [m1, m3]],
      ...            [[100, 50], [50, 200], [80, 400]], regularizer=0.,
      ...            identity_feature=True, misc_feature=False)
      >>> scopt.check_grad(m.func, m.func_deriv,
      ...                  np.ones(len(m.all_gmms)) / len(m.all_gmms) ) < 0.0001
      True
      >>> tok_weights = m.optimize()'''
   def __init__(self, gmms_list, errors_list, regularizer=1.0,
                identity_feature=True, misc_feature=False, verbose=False,
                init_by_feature='', min_value=1e-10):
      self.min_value = min_value
      self.init_by_feature = init_by_feature
      self.gmms_list = gmms_list
      self.errors_list = errors_list
      self.all_gmms = self.make_gmm_list()
      self.make_feature_vectors(identity_feature, misc_feature)
      self.regularizer = regularizer
      self.verbose = verbose
      self.deriv = np.zeros(len(self.feature_alphabet))
      self.n_fun_calls = 0
      self.n_deriv_calls = 0
      self.n_cache_hits = 0
      # cached data
      self.weight_sums = np.zeros(len(errors_list))
      self.weight_error_sums = np.zeros(len(errors_list))
      self.tweets = []
      self.hash = 0
      for (gmms,errors) in zip(gmms_list, errors_list):
         self.tweets.append(zip(gmms, errors))

   def make_gmm_list(self):
      return sorted(list(set([g for sublist in self.gmms_list
                              for g in sublist])), key=lambda gm:gm.tokens)

   def make_feature_vectors(self, identity_feature, misc_feature):
      '''Appends a sparse feature vector to each gmm. This also initializes
      feature_alphabet'''
      self.feature_alphabet = defaultdict(lambda: len(self.feature_alphabet))
      for g in self.all_gmms:
         g.feature_vector = defaultdict(lambda : 0)
         for (f,v) in g.features(identity_feature, misc_feature).iteritems():
            g.feature_vector[self.feature_alphabet[f]] = v

   def dot(self, feature_vector, x):
      'Dot product of feature_vector (a dict) and x (dense array)'
      return sum(x[fi] * v for (fi,v) in feature_vector.iteritems())

   def logistic(self, x):
      return 1.0 / (1.0 + np.exp(-x))

   def score_gmms(self, x):
      'Score is 1 / (1 + exp(-dot(g.feature_vector, x)))'
      for g in self.all_gmms:
         g.score = self.logistic(self.dot(g.feature_vector, x))

   # array modifications in place
   def update_cache(self, x):
      # Insane one-liner to get hash of a numpy array.
      # This tells us whether the array has changed.
      # FIXME: really need this? looks like func_deriv called exactly once per
      # call to func.
      h = int(hashlib.sha1(x.view(np.uint8)).hexdigest(), 16)
      if h != self.hash:
         self.hash = h
         self.f_value = 0.
         self.score_gmms(x)
         for ti,tweet in enumerate(self.tweets):
            self.weight_sums[ti] = 0.
            self.weight_error_sums[ti] = 0.
            for (gmm, error) in tweet:
               self.weight_error_sums[ti] += gmm.score * error
               self.weight_sums[ti] += gmm.score
            if self.weight_sums[ti] != 0.:
               self.f_value += self.weight_error_sums[ti] / self.weight_sums[ti]
         self.f_value += self.reg(x)
      else:
         self.n_cache_hits += 1

   def func(self, x):
      self.n_fun_calls += 1
      self.update_cache(x)
      return self.f_value

   def func_deriv(self, x):
      self.n_deriv_calls += 1
      self.update_cache(x)
      self.deriv.fill(0.0)
      for ti,tweet in enumerate(self.tweets):
         for (gmm,error) in tweet:
            entropy = (gmm.score
                       * (1.0 - gmm.score))
            if self.weight_sums[ti] * self.weight_sums[ti] == 0:
               part = 0.
            else:
               part = (entropy * (error * self.weight_sums[ti] -
                                  self.weight_error_sums[ti]) /
                       (self.weight_sums[ti] * self.weight_sums[ti]))
            for (feature_index,feature_value) in gmm.feature_vector.iteritems():
               self.deriv[feature_index] += part * feature_value
      self.reg_deriv(x)
      return self.deriv

   def reg(self, x):
      return self.regularizer * np.sum(x**2) / 2.0

   def reg_deriv(self,  x):
      self.deriv += self.regularizer * x

   def initialize_from_feature(self):
      init_vals = np.ones(len(self.feature_alphabet))
      for g in self.all_gmms:
         f = next(g.features(identity=True,misc=False).iterkeys())
         features = g.features(identity=False,misc=True)
         init_vals[self.feature_alphabet[f]] = \
             1 / (1 + features[self.init_by_feature]) - 0.5
      return init_vals

   def initialize_random(self):
      return np.array([u.rand.random() - 0.5 for
              i in range(0, len(self.feature_alphabet))])

   def optimize(self):
      'Run optimization and return dictionary of token->weight'
      if self.init_by_feature == '':
         init_vals = self.initialize_random()
      else:
         init_vals = self.initialize_from_feature()
      t_start = time.time()
      l.debug('minimizing obj f\'n with %d weights...' %
              len(self.feature_alphabet))
      l.debug('initial function value=%g' % self.func(init_vals))
      res = scopt.minimize(self.func, init_vals,
                           method='L-BFGS-B', jac=self.func_deriv,
                           options={'disp': self.verbose}, tol=1e-4)
      l.debug('minimized in %s; %d f calls and %d f\' calls (%d cache hits)'
              % (u.fmt_seconds(time.time() - t_start), self.n_fun_calls,
                 self.n_deriv_calls, self.n_cache_hits))
      l.debug('final function value=%g' % self.func(res.x))
      self.score_gmms(res.x)
      di = dict([(next(gmm.tokens.iterkeys()),
                  max(self.min_value, gmm.score))
                 for gmm in self.all_gmms])
      if self.verbose:
         for (fv,fi) in self.feature_alphabet.iteritems():
            l.debug('feature weight %s=%g' % (fv,res.x[fi]))
         for (t,w) in di.iteritems():
            l.debug('token weight %s=%s'%(t,str(w)))
      # clean up
      for g in self.all_gmms:
         g.feature_vector = None
      return di

# test that self.all_gmms has stable order
testable.register('''
>>> import gmm
>>> import random
>>> def test_random():
...   u.rand = random.Random(123)
...   gmm.Token.parms_init({})
...   mp = geos.MultiPoint(geos.Point(1,2), geos.Point(3,4), srid=4326)
...   m1 = gmm.Geo_GMM.from_fit(mp, 1, 'a')
...   m2 = gmm.Geo_GMM.from_fit(mp, 2, 'b')
...   m3 = gmm.Geo_GMM.from_fit(mp, 1, 'c')
...   m = Weight([[m1, m2], [m2, m3], [m1, m3]],
...            [[100, 50], [50, 200], [80, 400]], identity_feature=True,
...            misc_feature=False)
...   return list(m.all_gmms)
>>> all((test_random()[0].tokens == test_random()[0].tokens for i in xrange(100)))
True
''')
