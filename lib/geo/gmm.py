'''This module contains models with a few variations on estimating locations
   with fitted Gaussian mixture models (GMMs).'''

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

from __future__ import division

from collections import Counter, OrderedDict
import operator
import math
from pprint import pprint
import sys
import time

from django.contrib.gis import geos
import matplotlib.pyplot as plt  # for testing
import numpy as np
import osgeo.gdal as ogdal
from sklearn.datasets.samples_generator import make_blobs
import sklearn.mixture

from . import base
from . import pipeline
from . import srs
from . import optimize
import multicore
import testable
import tweet
import u

l = u.l

# This is a reference to the class parameters dictionary; it is set in
# Model.parms_init(), and the defaults are immediately below. Yes, it's an
# awkward interaction between class and module. We do it this way because
# joblib can only parallelize functions, not methods.
#
# FIXME: This approach probably depends on only one instance of one class from
# this module being instantiated per process.
model_parms = None

# Default model parameters. It's a function rather than a variable because we
# need to refer to functions which are not yet defined.
def MODEL_PARMS_DEFAULT():
   return { 'best_point_f':           best_point_weighted_avg,
            'component_ct_max':       20,
            'component_ct_min':       1,
            'component_sz_min':       3,
            'covariance_type':        'full',
            'gmm_fit_f':              gmm_fit_log_heuristic,
            'min_covar':              0.001,
            'opt_feature_id':         1,
            'opt_feature_misc':       0,
            'opt_reg':                1,
            'opt_init':               '',
            'weight_f':               wt_inv_feature,
            'weight_feature':         'covar_sumprod',
            'weight_min':             0.001,
            'wt_inv_error_exponent':  4.0,
            'wt_inv_min_tweets':      3,
            'wt_inv_sample_ct':       100 }


def gmm_fit_tokenpoints(token, points):
   '''Given a (token, points) pair, return a (token, GMM) fitted to the points
      using the configure strategy. This interface is provided for
      compatibility with iterators that yield such pairs.'''
   assert (points.geom_type == 'MultiPoint')
   gmm = model_parms['gmm_fit_f'](token, points)
   # FIXME: This is extremely chatty, so I'm leaving it commented out. Perhaps
   # we need another level of logging below DEBUG.
   #l.debug('fit %d gaussians to %d points for token <%s>'
   #        % (gmm.n_components, len(points), token))
   # While gmm contains token, we return a tuple because many callers want to
   # cache a mapping from token to GMM.
   return (token, gmm)

# Options for parameter gmm_fit_f:

def gmm_fit_ternary(points):
   return do_gmm_fit_ternary(points, model_parms['component_ct_min'],
                             model_parms['component_ct_max'])

def gmm_fit_exhaustive(points):
   ''' Exhaustive search for n_components that minimizes BIC score.

   #>>> Token.parms_init({'component_ct_min':1, 'component_ct_max':20})
   #>>> g = gmm_fit_exhaustive([[1],[1.1],[1.12],[1.09], [6],[6.2],[6.1]])
   #>>> g.n_components
   #2'''

   lowest_bic = np.infty
   bic = []
   n_components_range = range(model_parms['component_ct_min'],
                              min(model_parms['component_ct_max'],
                              len(points)))
   for n_components in n_components_range:
      gmm = fit_gmm(points, n_components)
      bic.append(gmm.bic(np.array(points)))
      if bic[-1] < lowest_bic:
         lowest_bic = bic[-1]
         best_gmm = gmm
   return best_gmm

def gmm_fit_fixed(points):
   ''' n_components = component_ct_min

   #>>> Token.parms_init({'component_ct_min':2, 'component_ct_max':2})
   #>>> gmm_fit_fixed([[0],[1],[2],[3],[4]]).n_components
   #2
   #>>> gmm_fit_fixed([[0],[1]]).n_components
   #1'''
   n = min(len(points)//2, model_parms['component_ct_min'])
   return fit_gmm(points, n)

def gmm_fit_log_heuristic(token, mp):
   '''n_components = log(k)/2 for k points
      Respects component_ct_max/min.

      >>> Token.parms_init({'component_ct_min':1, 'component_ct_max':20})
      >>> ps = [geos.Point(xy) for xy in zip(xrange(32), xrange(32))]
      >>> mp16 = geos.MultiPoint(ps[:16], srid=4326)
      >>> mp32 = geos.MultiPoint(ps, srid=4326)
      >>> gmm_fit_log_heuristic('foo', mp16).n_components
      2
      >>> gmm_fit_log_heuristic('bar', mp32).n_components
      3'''
   n = (int(round(math.log(len(mp), 2)/2)))
   n = min(n, model_parms['component_ct_max'])
   n = max(n, model_parms['component_ct_min'])
   return Geo_GMM.from_fit(mp, n, token)

def gmm_fit_sqrt_heuristic(points):
   ''' n_components = sqrt(k//2) for k points
       Respects component_ct_max/min.

       #>>> Token.parms_init({'component_ct_min':1, 'component_ct_max':20})
       #>>> gmm_fit_sqrt_heuristic([[i] for i in range(0,10)]).n_components
       #2
       #>>> gmm_fit_sqrt_heuristic([[i] for i in range(0,50)]).n_components
       #5'''
   n = (int(round(math.sqrt(len(points)/2))))
   n = min(n, model_parms['component_ct_max'])
   n = max(n, model_parms['component_ct_min'])
   return fit_gmm(points, n)

def score_to_prob(s):
   return 1.0 / (1.0 + np.exp(-s))

def best_gmm(scores, gmms):
   return gmms[min([i for i in range(0, len(scores))],
                   key=lambda s: scores[s])]

def ternary_search(data, min_i, min_score, min_gmm, max_i, max_score, max_gmm):
   '''Searches for optimal number of gaussians using Ternary
      Search. Assumes BIC score is monotonic.'''
   left_third = (2 * min_i + max_i) // 3
   right_third = (min_i + 2 * max_i) // 3
   left_third_gmm = fit_gmm(data, left_third)
   right_third_gmm = fit_gmm(data, right_third)
   left_third_score = left_third_gmm.bic(data)
   right_third_score = right_third_gmm.bic(data)
   if max_i - min_i <= 3:
      return best_gmm([min_score, left_third_score,
                       right_third_score, max_score],
                      [min_gmm, left_third_gmm,
                       right_third_gmm, max_gmm])

   if left_third_score > right_third_score:
      return ternary_search(data, left_third, left_third_score, left_third_gmm,
                            max_i, max_score, max_gmm)
   else:
      return ternary_search(data, min_i, min_score, min_gmm,
                            right_third, right_third_score, right_third_gmm)

def do_gmm_fit_ternary(data, n_min, n_max):
   '''Ternary search for GMM with optimal number of components from n_min to
      n_max (both inclusive). n_max is clamped at len(data) - 1.

      NOTE: We considered mixture.DPGMM (which obviates need to pick N), but
      this module was not working at time of writing:
      http://sourceforge.net/mailarchive/message.php?msg_id=29984164'''
   n_components_range = range(n_min, min(n_max, len(data)-1) + 1)
   min_gmm = fit_gmm(data, n_components_range[0])
   max_gmm = fit_gmm(data, n_components_range[-1])
   npdata = np.array(data)
   return ternary_search(npdata, n_components_range[0], min_gmm.bic(npdata),
                         min_gmm, n_components_range[-1],
                         max_gmm.bic(npdata), max_gmm)


# Options for parameter best_point_f

def best_point_f(model):
   return model_parms['best_point_f'](model)

def best_point_means(model):
    return model.means_[max([i for i in range(0, len(model.means_))],
                            key=lambda w: model.score([model.means_[i]])[0])]

def best_point_weighted_avg(model):
   '''Return the mean of the means in the model, weighted by component
      weights. For example:

      >>> Token.parms_init({'component_sz_min':1})
      >>> mp = geos.MultiPoint([geos.Point(xy)
      ...                       for xy
      ...                       in [[1,1],[1.1,1],[.9,1.1], [5,5],[4.5,5]]])
      >>> g = Geo_GMM.from_fit(mp, 2, 'foo')
      >>> best_point_weighted_avg(g)
      array([ 2.5 ,  2.62])'''
   return np.average(model.means_, axis=0, weights=model.weights_)

def cae(token, points, token_gmms):
   m = token_gmms[token]
   m.prepare(0.95)
   av = np.average(points, axis=0)
   avg_p = geos.Point(*av, srid=points[0].srid)
   w = 1/(1 + m.cae(avg_p))
   return w

def relevant_gmms(tokens, token_gmms):
   return [ token_gmms[t] for t in tokens if t in token_gmms ]


# Options for parameter weight_f. This is a function which takes a token:Model
# mapping, an iterator of tweets, and token:MultiPoint mapping and returns a
# token:weight dictionary.

def cae_opt(tms, tweets, tokenpoints):
   '''Optimize token_weights to minimize CAE over all training tweets'''
   l.debug('preparing token models')
   t_start = time.time()
   for g in tms.values():
      g.populate_samples(100)
   l.debug('done preparing in %s' % (u.fmt_seconds(time.time() - t_start)))
   gmms_list = []
   errors_list = []
   l.debug('computing CAE for all tweets')
   t_start = time.time()
   for tw in tweets:
      r_gmms = relevant_gmms(tw.tokens, tms)
      if (len(r_gmms) == 0):
         continue
      errors = [max(0.00001, g.cae(tw.geom)) for g in r_gmms]
      gmms_list.append(r_gmms)
      errors_list.append(errors)
   l.debug('done computing CAE in %s' % (u.fmt_seconds(time.time() - t_start)))
   return optimize.Weight(gmms_list, errors_list,
                          regularizer=model_parms['opt_reg'],
                          identity_feature=model_parms['opt_feature_id'],
                          misc_feature=model_parms['opt_feature_misc'],
                          init_by_feature=model_parms['opt_init']
                          ).optimize()

# FIXME: DRY (cae_opt)
def sae_opt(tms, tweets, tokenpoints):
   '''Optimize token_weights to minimize SAE over all training tweets'''
   l.debug('preparing token models')
   t_start = time.time()
   # FIXME: multicore?
   for g in tms.values():
      g.populate_best_point()
   l.debug('done preparing in %s' % (u.fmt_seconds(time.time() - t_start)))
   gmms_list = []
   errors_list = []
   l.debug('computing MSAE for all tweets')
   t_start = time.time()
   for tw in tweets:
      r_gmms = relevant_gmms(tw.tokens, tms)
      if (len(r_gmms) == 0):
         continue
      errors = [g.sae(tw.geom) for g in r_gmms]
      gmms_list.append(r_gmms)
      errors_list.append(errors)
   l.debug('done computing SAE in %s' % (u.fmt_seconds(time.time() - t_start)))
   return optimize.Weight(gmms_list, errors_list,
                          regularizer=model_parms['opt_reg'],
                          identity_feature=model_parms['opt_feature_id'],
                          misc_feature=model_parms['opt_feature_misc'],
                          init_by_feature=model_parms['opt_init']).optimize()

def wt_inv_error_sae(tms, tweets, tokenpoints):
   return wt_inv_error(tms, tweets, tokenpoints, 'sae')

def wt_inv_error_cae(tms, tweets, tokenpoints):
   return wt_inv_error(tms, tweets, tokenpoints, 'cae')

def wt_inv_error(tms, tweets, tokenpts, errattr):
   '''Weight of token T is |1/E^x|, where E is the mean error between T and
      each tweet in tweets having that token, using measure errattr ('sae' or
      'cae'), and x is model parm wt_inv_error_exponent. The number of samples
      used in computing CAE is model parm wt_inv_sample_ct. If the number of
      tweets with the token is less than model parm wt_inv_min_tweets, the
      weight is 0.'''
   l.debug('computing inverse errors')
   t1 = time.time()
   # We work in chunks to keep memory use down. The chunk size is currently
   # not configurable, though we could make it so if needed.
   models = tms.values()
   weights = dict()
   x = model_parms['wt_inv_error_exponent']
   for chunk in u.groupn(models, 20000):
      weights.update((tok, min(1, abs(1/(1+err**x))))
                     for (tok, err)
                     in multicore.do(model_error, (errattr, tokenpts), chunk))
      l.debug('inverse error chunk completed')
   dur = time.time() - t1
   l.debug('computed inverse errors in %s (%.2gs per token)'
           % (u.fmt_seconds(dur), dur / len(models)))
   return weights

def model_error(errattr, tokenpts, g):
   '''Return the error (using measure errattr) of model g on token points
      looked up in tokenpts. If there are fewer than model parm
      wt_inv_min_tweets for the token, return positive infinity.'''
   # FIXME: awkard to return (token, error) tuple? just return error and let
   # caller zip() it up?
   assert (len(g.explanation) == 1)
   token = next(g.explanation.iterkeys())
   points = tokenpts[token]
   assert (points.geom_type == 'MultiPoint')
   if (len(points) < model_parms['wt_inv_min_tweets']):
      return np.inf
   assert (not g.prepared)
   # This if/else is kind of awkward. populate_samples() is pretty
   # heavyweight, so we certainly shouldn't do that unless we have to. But
   # still, I'm uncomfortable here...
   if (errattr == 'sae'):
      g.populate_best_point()
   elif (errattr == 'cae'):
      g.populate_samples(model_parms['wt_inv_sample_ct'])
   else:
      assert False, 'unreachable'
   err = np.mean([getattr(g, errattr)(pt) for pt in points])
   g.unprepare()
   return (token, err)

def scale(token_weights):
   '''Scale weights to be positive, if needed, by exp(x - max(token_weights))

      >>> pprint(scale({'a':-1,'b':1}))
      {'a': 0.135..., 'b': 1.0}
      >>> pprint(scale({'a':10,'b':5}))
      {'a': 10, 'b': 5}'''
   if any(v < 0 for v in token_weights.itervalues()):
      max_v = max(token_weights.itervalues())
      return {t:math.exp(v - max_v)
              for (t,v) in token_weights.iteritems()}
   else:
      return token_weights

def inverse(token_weights):
   '''Make small values big and big values small. All will be positive in the
      end, in range (1,+Infty).

      >>> pprint(inverse({'a':-1,'b':1}))
      {'a': 3.0, 'b': 1.0}
      >>> pprint(inverse({'a':-100,'b':100}))
      {'a': 201.0, 'b': 1.0}'''
   if any(v < 0 for v in token_weights.itervalues()):
      max_v = max(token_weights.itervalues())
      return {t:max_v + 1. - v
              for (t,v) in token_weights.iteritems()}
   else:
      return token_weights

def wt_neg_feature(tms, tweets, tokenpoints):
   '''Weight by max(weights) + 1 - w, where w is a weight_feature. This means
      that small weights become large, large weights become small, and all
      weights are positive in range (1,+Infty).'''
   m = { t: m.features()[model_parms['weight_feature']]
         for (t, m) in tms.iteritems() }
   m = inverse(m)
   return m

def wt_inv_feature(tms, tweets, tokenpoints):
   '''Weight by the inverse of feature name specified by parameter
      weight_feature). If negative numbers exist, shift all values to be
      positive.'''
   m = { t: 1 / (1 + m.features()[model_parms['weight_feature']])
         for (t, m) in tms.iteritems() }
   return scale(m)


class Geo_GMM(base.Location_Estimate, sklearn.mixture.GMM):
   '''This is a GMM with a geographic interpretation, which also serves as a
      location estimate (hence the multiple inheritance). Adds the following
      attributes:

        samples .......... List of (Point, log probability, component index)
                           tuples sampled from the model, ordered by
                           descending log probability. WARNING: These samples
                           are *not* guaranteed to be in-bounds (i.e., valid
                           locations on the globe).

        samples_inbound .. geos.MultiPoint of above which are in-bounds.'''

   # FIXME: Lame to use tuples for the samples list. Better to use objects?

   def __init__(self, *args, **kwargs):
      self.samples = None
      self.samples_inbound = None
      u.call_kw(base.Location_Estimate.__init__, self, **kwargs)
      u.call_kw(sklearn.mixture.GMM.__init__, self, **kwargs)

   @property
   def explanation(self):
      return self.tokens

   @classmethod
   def combine(class_, gmms, weights, coverage):
      '''Combine Geo_GMMs using gmm_combine_f. gmms is an iterable of Geo_GMMs
         (each with exactly one token of weight 1), while weights is a (token,
         weight) mapping that must be a superset of the tokens in gmms.

         GMMs with weights close to zero are omitted; at least one must
         remain. All component SRIDs must be the same, as must all covariance
         types. The result is a prepared Geo_GMM will all the
         Location_Estimate juicyness.

         For example:

         >>> Token.parms_init({'component_sz_min':1})
         >>> mp = geos.MultiPoint(geos.Point(1,2), geos.Point(3,4), srid=4326)
         >>> m1 = Geo_GMM.from_fit(mp, 1, 'foo')
         >>> m2 = Geo_GMM.from_fit(mp, 2, 'bar')
         >>> m3 = Geo_GMM.from_fit(mp, 1, 'baz')
         >>> combined = Geo_GMM.combine([m1, m2, m3],
         ...                            { 'foo':2, 'bar':3, 'baz':1e-6 }, 0.95)
         >>> combined.weights_
         array([ 0.4,  0.3,  0.3])
         >>> pprint(combined.explanation)
         {'bar': 0.6, 'foo': 0.4}
         >>> combined.n_points
         4
         >>> [combined.sample(5) for i in xrange(100)] and None
         >>> combined.srid
         4326
         >>> combined.pred_region.geom_type
         u'MultiPolygon'
         >>> combined.pred_coverage
         0.95
         >>> print Geo_GMM.combine([m1, m2, m3],
         ...                 { 'foo':0, 'bar':0, 'baz':0 }, 0.95)
         None
         '''
      # sanity checks
      assert (len(gmms) >= 1)
      srid = gmms[0].srid
      covariance_type = gmms[0].covariance_type
      assert (srid is not None)
      def weight(g):
         return weights[next(g.tokens.iterkeys())]
      for g in gmms:
         assert (g.srid == srid)
         assert (g.covariance_type == covariance_type)
         assert (len(g.tokens) > 0)
         assert (weight(g) >= 0)
         # following aren't fundamental, just not yet supported
         assert (len(g.tokens) == 1)
         assert (next(g.tokens.itervalues()) == 1.0)
      # remove GMMs that don't have enough weight
      max_weight = max([weight(g) for g in gmms])
      min_weight = max_weight * model_parms['weight_min']
      gmms = filter(lambda g: weight(g) > min_weight, gmms)
      # all weights are 0. cannot locate.
      if (max_weight == 0):
         return None
      assert (len(gmms) >= 1)
      # renormalize weights
      relevant_weights = { t: weights[t]
                           for t in sum([g.tokens.keys() for g in gmms], []) }
      total_weight = sum(relevant_weights.itervalues())
      weights = { t: w / total_weight
                  for (t, w) in relevant_weights.iteritems() }
      # build a skeleton GMM
      n_components = sum([g.n_components for g in gmms])
      new = class_(n_components=n_components, covariance_type=covariance_type)
      # populate the new GMM
      new.srid = srid
      new.means_ = np.concatenate([g.means_ for g in gmms])
      new.covars_ = np.concatenate([g.covars_ for g in gmms])
      new.weights_ = np.concatenate([g.weights_ * weight(g) for g in gmms])
      new.converged_ = True
      new.tokens = weights
      new.n_points = sum([g.n_points for g in gmms])
      # prepare
      new.prepare(coverage)
      return new

   @classmethod
   def filter_small_components(class_, m, data):
      '''Remove components with fewer than component_sz_min points. If none
         remain, re-fit with one component.
         >>> Token.parms_init({'component_sz_min':2})
         >>> x,y = make_blobs(n_samples=100, centers=[[10,10], [20,20]],
         ...                  n_features=2, random_state=100)
         >>> x = np.vstack((x, [100,100])) # outlier
         >>> mp = geos.MultiPoint([geos.Point(tuple(xy)) for xy in x])
         >>> m = Geo_GMM.from_fit(mp, 3, 'foo')
         >>> m.n_components
         2
         >>> mp = geos.MultiPoint([geos.Point((10,10)), geos.Point((20,20))])
         >>> m = Geo_GMM.from_fit(mp, 2, 'foo')
         >>> m.n_components
         1'''
      cts = Counter(m.predict(data))
      tokeep = [idx for (idx,ct) in cts.items()
                if ct >= model_parms['component_sz_min']]
      if len(tokeep) == 0:
         m.n_components = 1
         m.fit(data)
      else:
         m.means_ = m.means_[tokeep]
         m.covars_ = m.covars_[tokeep]
         m.weights_ = m.weights_[tokeep]
         m.weights_ = m.weights_ / sum(m.weights_)
         m.n_components = len(tokeep)
      return m

   @classmethod
   def from_fit(class_, mp, n_components, tokens=tuple()):
      '''Given a MultiPoint, return a new Geo_GMM fitted to those points. If
         given, tokens is an iterable of tokens or a single token string.'''
      new = class_(n_components=n_components,
                   covariance_type=model_parms['covariance_type'],
                   min_covar=model_parms['min_covar'],
                   random_state=u.rand_np, n_iter=1000)
      data = np.array(mp, dtype=np.float)  # mp.coords is slow
      new.fit(data)
      new = Geo_GMM.filter_small_components(new, data)
      new.srid = mp.srid
      if (isinstance(tokens, basestring)):
         tokens = [tokens]
      new.tokens = { t:1 for t in tokens }
      new.n_points = mp.num_geom
      new.aic_cache = new.aic(data)
      new.bic_cache = new.bic(data)

      # use average of X and Y variance as the variance
      new.var_cache = np.mean((data[:,0].var(), data[:,1].var()))
      return new

   def cae(self, pt):
      return np.mean(srs.geodesic_distance_mp(pt, self.samples_inbound_mp))

   def contour(self, pt):
      score = self.score_pt(pt)
      idx = sum(score < i[1] for i in self.samples)
      return (idx / len(self.samples))

   def coverst_p_real(self, pt):
      return self.score_pt(pt) > self.pred_region_threshold

   def likelihood_polygon(self,pg):
      '''>>> Token.parms_init({'component_sz_min':1})
         >>> mp = geos.MultiPoint(geos.Point(1,1), geos.Point(10,10), srid=4326)
         >>> m = Geo_GMM.from_fit(mp, 2, 'foo')
         >>> c = Geo_GMM.combine([m], {'foo':1 }, 0.95)
         >>> c.likelihood_polygon(geos.Polygon.from_bbox((0.9,0.9,1.1,1.1)))
         0.501
         >>> c.likelihood_polygon(geos.Polygon.from_bbox((0.95,0.95,1.05,1.05)))
         0.399'''
      # returns proportion of samples contained in pg
      return sum(pg.contains(p[0]) for p in self.samples) / len(self.samples)

   def likelihood_polygons(self, polygons, threshold=0.001):
      '''Return (index, probability) tuples for the likelihood of each
         polygon, trimmed by threshold.

         >>> Token.parms_init({'component_sz_min':1})
         >>> mp = geos.MultiPoint(geos.Point(1,1), geos.Point(10,10), srid=4326)
         >>> m = Geo_GMM.from_fit(mp, 2, 'foo')
         >>> combined = Geo_GMM.combine([m], {'foo':1 }, 0.95)
         >>> big = geos.Polygon.from_bbox((0.9,0.9,1.1,1.1))
         >>> small = geos.Polygon.from_bbox((0.95,0.95,1.05,1.05))
         >>> combined.likelihood_polygons([big, small])
         [(0, 0.501), (1, 0.392)]'''
      scores = [(i, self.likelihood_polygon(p))
                for (i,p) in enumerate(polygons)]
      return [(i, s) for (i,s) in scores if s >= threshold]

   def dump_geoimage(self, basename, width_px):
      # FIXME: This method is a mess and needs to be cleaned & split into
      # several other methods.
      #
      # The GDAL documentation for Python is pretty poor, so this is cobbled
      # together from a bunch of Googling. Notable sources:
      #
      #   https://gist.github.com/205115
      #   http://www.gdal.org/gdal_tutorial.html
      #   http://trac.osgeo.org/gdal/wiki/PythonGotcha
      #   http://www.gdal.org/frmt_gtiff.html

      # Find the bounds and image dimensions in this estimate's SRS, aiming
      # for square pixels (which of course may not be square in other SRS).
      def t(xy):
         return srs.transform(geos.Point(xy, srid=srs.SRID_WGS84), self.srid)
      xmin = t((base.GEOIMG_LONMIN, 0)).x
      xmax = t((base.GEOIMG_LONMAX, 0)).x
      ymin = t((0, base.GEOIMG_LATMIN)).y
      ymax = t((0, base.GEOIMG_LATMAX)).y
      height_px = int(width_px * (xmax - xmin) / (ymax - ymin))

      # Evaluate the model across the world. (FIXME: This could be sped up
      # with some smarter choices of bounds.) (FIXME: should we have
      # endpoint=False?)
      xs = np.linspace(xmin, xmax, num=width_px)
      ys = np.linspace(ymin, ymax, num=height_px)
      xys = np.dstack(np.meshgrid(xs, ys)).reshape((width_px * height_px, 2))
      # FIXME: Token GMMs have a bad self.score, introduced by optimize.py;
      # see issue #32. This works around the problem in unpickled objects that
      # can't be fixed by simply updating the code; it patches the live
      # objects to restore the method. It should be removed when no longer
      # needed.
      l.warning('workaround code for private issue #32 active')
      import numpy
      if (isinstance(self.score, numpy.float64)):
         l.debug('workaround code for private issue #32 triggered')
         from types import MethodType
         self.score = MethodType(self.__class__.score, self, self.__class__)
      probs = score_to_prob(self.score(xys))
      probs = probs.reshape((height_px, width_px))

      # FIXME: There is a bug in libgdal
      # (http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=695060) which
      # prevents it from correctly interpreting files that have distance units
      # other than meters. Thus, if we are using one of our SRS with km or Mm
      # units, use the following kludge to convert the result to the
      # meter-based equivalent.
      srid_export = self.srid
      (base_srid, r) = divmod(self.srid, 10)
      if (base_srid >= 10000):
         srid_export = base_srid
         [xmin, xmax, ymin, ymax] = [x*10**r for x in [xmin, xmax, ymin, ymax]]

      # Write the results as a GeoTIFF. First transformation is to boost the
      # low values to make them more visible in the plot. b>0 is "bendiness".
      l.debug("max probability before bending = %g" % (probs.max()))
      b = 4.0
      probs = (b * probs + probs) / (b * probs + 1)
      l.debug("max probability after bending = %g" % (probs.max()))
      # We scale the probability range to [0,255] so that we can use the Byte
      # type and JPEG compression (which saves approximately 30x).
      probs = (255/probs.max() * probs).clip(0, 255).astype(np.uint8)
      driver = ogdal.GetDriverByName('GTiff')
      out = driver.Create(basename + '.tif',
                          width_px, height_px, 1, ogdal.GDT_Byte,
                          ['COMPRESS=JPEG', 'JPEG_QUALITY=95',
                           'PHOTOMETRIC=MINISWHITE'])
      # arbitrary key, value metadata; doesn't appear in QGIS
      #out.SetMetadataItem('foo', 'bar')
      # Affine transform from image space to projected space. I don't quite
      # understand what is going on here; the resulting image has upper left
      # and lower left corners reversed according to gdalinfo (and same for
      # right). However, it displays fine in QGIS. An alternative is to offer
      # ymax and invert the pixel size (making it negative), which gives
      # corners that seem right but then the image is upside down.
      # http://gdal.org/classGDALDataset.html#af9593cc241e7d140f5f3c4798a43a668
      out.SetGeoTransform([xmin, (xmax - xmin) / width_px, 0,
                           ymin, 0, (ymax - ymin) / height_px])
      out.SetProjection(srs.SRS[srid_export].wkt)
      out.GetRasterBand(1).WriteArray(probs)
      # In order to correctly display in QGIS, you need to compute the exact
      # statistics. A bug prevents QGIS from doing this
      # http://hub.qgis.org/issues/6496(), and also if use this call, then
      # it's embedded in the file and no auxiliary .xml file is created.
      out.GetRasterBand(1).GetStatistics(0,1)

   def features(self, identity=True, misc=True):
      '''Return an OrderedDict of some features that might be worth judging
         the quality of this object on. If identity is True, include a
         uniquely named feature with value 1; if misc is True, include
         everything else. For example:

         >>> Token.parms_init({'component_sz_min':1})
         >>> points = [geos.Point(xy) for xy in ((1,2), (3,4), (6,5), (9,7))]
         >>> mp = geos.MultiPoint(points, srid=4326)
         >>> g = Geo_GMM.from_fit(mp, 2, 'tx foo')
         >>> for (k, v) in g.features().iteritems(): print '%s: %s' % (k, v)
         Geo_GMM/...: 1
         tx: 1
         one: 1
         n_components: 2
         n_points: 4
         aic: 22.36...
         bic: 15.61...
         variance: 6.21...
         variance_comp: 3.10...
         variance_pt: 1.55...
         covar_sumsum: 10.25...
         covar_sumprod: 6.07...
         covar_sumsum_comp: 5.12...
         covar_sumsum_pt: 2.56...
         covar_sumprod_comp: 3.03...
         covar_sumprod_pt: 1.51...

         Warning: the identity feature is only valid for the lifetime of this
         object. In particular, if you pickle and rebuild this object, you
         will get a different identity feature.
         '''
      assert (identity or misc)
      od = OrderedDict()
      if (identity):
         od['%s/%d' % (self.__class__.__name__, id(self))] = 1
      if (misc):
         od.update({ t[:2]:1 for t in self.tokens.iterkeys() })  # tweet field
         od['one'] = 1
         od['n_components'] = self.n_components
         od['n_points'] = self.n_points
         try:
            od['aic'] = self.aic_cache
            od['bic'] = self.bic_cache
            od['variance'] = self.var_cache
            od['variance_comp'] = od['variance'] / self.n_components
            od['variance_pt'] = od['variance'] / self.n_points
         except AttributeError:
            pass
         od['covar_sumsum'] = self.covars_.sum()
         od['covar_sumprod'] = sum([cv.prod() for cv in self.covars_])
         od['covar_sumsum_comp'] = od['covar_sumsum'] / self.n_components
         od['covar_sumsum_pt'] = od['covar_sumsum'] / self.n_points
         od['covar_sumprod_comp'] = od['covar_sumprod'] / self.n_components
         od['covar_sumprod_pt'] = od['covar_sumprod'] / self.n_points
      return od

   def populate_best_point(self):
      self.best_point = geos.Point(tuple(best_point_f(self)), srid=self.srid)

   def populate_pred_region_real(self, trim=True):
      # what's the contour value?
      threshold_idx = int(round(self.pred_coverage * len(self.samples)))
      self.pred_region_threshold = self.samples[threshold_idx][1]
      bests = self.samples[:threshold_idx]
      # compute contours
      regions = []
      for i in xrange(self.n_components):
         points = filter(lambda j: j[2]==i, bests)
         if (len(points) < 3):
            # can't make a polygon with less than 3 vertices, skip
            continue
         points = geos.MultiPoint([i[0] for i in points], srid=self.srid)
         regions.append(points.convex_hull)
      # create a multipolygon and clean up
      assert (len(regions) > 0)
      pr = geos.MultiPolygon(regions, srid=self.srid).cascaded_union
      if (trim):
         pr = srs.trim(pr)
      if (pr.geom_type == 'Polygon'):
         # cascaded_union can collapse a MultiPolygon into a single Polygon
         pr = geos.MultiPolygon([pr], srid=self.srid)
      assert (pr.geom_type == 'MultiPolygon')
      self.pred_region = pr

   def prepare_real(self):
      self.populate_samples(model_parms['mc_sample_ct'])

   def populate_samples(self, sample_ct):
      sraw = [geos.Point(tuple(i), srid=self.srid)
              for i in self.sample(sample_ct, u.rand_np)]
      evals = self.eval([i.coords for i in sraw])
      logprobs = evals[0]
      component_is = [np.argmax(i) for i in evals[1]]
      self.samples = zip(sraw, logprobs, component_is)
      self.samples.sort(reverse=True, key=operator.itemgetter(1))
      mp = geos.MultiPoint([i[0] for i in self.samples], srid=self.srid)
      self.samples_inbound_mp = srs.trim(mp)

   def score_pt(self, pt):
      return self.score((pt.coords,))[0]

   def unprepare(self):
      self.samples = u.Deleted_To_Save_Memory()
      self.samples_inbound_mp = u.Deleted_To_Save_Memory()
      base.Location_Estimate.unprepare(self)


class Model(base.Model):

   parms_default = u.copyupdate(base.Model.parms_default,
                                MODEL_PARMS_DEFAULT())

   @classmethod
   def parms_init(class_, parms, **kwargs):
      super(Model, class_).parms_init(parms, **kwargs)
      # See above for more on this kludge.
      global model_parms
      model_parms = class_.parms


class Message(Model):
   ''' Gaussian Mixture Model created for every message based on
       location of tokens in that message.'''

   def build(self):
      'Just store map of all token/location pairs'
      self.warn_if_parallel()
      self.token_iterator = feature_select(self.tokens)
      self.tokens = {token:points for (token,points) in self.token_iterator}

   def locate(self, tokens, confidence):
      tweet_points = []
      for token in tokens:
         if token in self.tokens:
            tweet_points.extend(self.tokens[token])
      if len(tweet_points) == 0:
         return None
      else:
         model = gmm_fit_tokenpoints('all',geos.MultiPoint(tweet_points))[1]
         return Location_Estimate(model, confidence, self.srid)


class Token(Model):
   '''Gaussian Mixture Model created for every token. Locate method
      combines models according to gmm_combine_f(). For example:

      >>> Token.parms_init({})
      >>> mp = geos.MultiPoint(geos.Point(30, 60), geos.Point(40,70),
      ...                      srid=u.WGS84_SRID)
      >>> m = Token([('foo', mp)], u.WGS84_SRID)
      >>> m.build()
      >>> m.locate(['foo'], 0.95).best_point.coords
      (34.999..., 64.999...)'''

   def build(self):
      self.token_gmms = dict(multicore.do(gmm_fit_tokenpoints,
                                          (), self.tokens.items()))
      self.token_weights = model_parms['weight_f'](self.token_gmms,
                                                   self.tweets, self.tokens)

   def locate(self, tokens, confidence):
      r_gmms = relevant_gmms(tokens, self.token_gmms)
      if (len(r_gmms) == 0):
         return None
      else:
         return Geo_GMM.combine(r_gmms, self.token_weights, confidence)

   def token_summary(self, token):
      od = Model.token_summary(self, token)
      od.update(self.token_gmms[token].features(identity=False, misc=True))
      return od


class All_Tweets(Model):
   '''Single Gaussian Mixture Model created for all tokens.
      >>> All_Tweets.parms_init({})
      >>> mp1 = geos.MultiPoint(geos.Point(30, 60), srid=u.WGS84_SRID)
      >>> mp2 = geos.MultiPoint(geos.Point(40,70), srid=u.WGS84_SRID)
      >>> m = All_Tweets([('foo', mp1), ('bar', mp2)], u.WGS84_SRID)
      >>> m.build()
      >>> m.locate(['foo'], 0.95).best_point.coords
      (34.999..., 64.999...)
      >>> m.locate(['bar'], 0.95).best_point.coords
      (34.999..., 64.999...)'''

   def build(self):
      self.warn_if_parallel()
      allpoints = geos.MultiPoint([pts for sublist in self.tokens.itervalues()
                                   for pts in sublist],
                                  srid=self.srid)
      l.debug('fitting All_Tweets to %d points...' % len(allpoints))
      self.global_model = gmm_fit_tokenpoints('_all_tweets_', allpoints)[1]

   def locate(self, tokens, confidence):
      # FIXME: wasteful to repeatedly prepare the same model?
      self.global_model.prepare(confidence)
      return self.global_model


# FIXME: figure out how to pass model_parms for each submodel here
class Message_All_Pipeline(pipeline.Model):
   def __init__(self, token_iterator):
      assert False, 'unimplemented'
      pipeline.Model.__init__(self, [Message(token_iterator),
                                     All_Tweets(token_iterator)])

class Token_All_Pipeline(pipeline.Model):
   def __init__(self, token_iterator):
      assert False, 'unimplemented'
      pipeline.Model.__init__(self, [Token(token_iterator),
                                     All_Tweets(token_iterator)])


### Tests ###

# Test passes as of sklearn.13-git
testable.register('''

# Test that fitting respects consistent random state.
>>> def test_r():
...   r = np.random.mtrand.RandomState(1234)
...   m = sklearn.mixture.GMM(n_components=2, random_state=r)
...   m.fit([1, 1.1, 2, 2.2])
...   return m.sample(10, r)
>>> all((test_r().tolist() == test_r().tolist() for i in xrange(100)))
True

''')

def test_interactive():
   import cProfile

   #prof = cProfile.Profile()
   #prof.enable()
   u.logging_init('inter', verbose_=True)
   test_error_metrics()
   test_interactive_real()

   #prof.disable()
   #prof.dump_stats('profile.out')

def test_interactive_real():
   sample_ct = 1000
   test_ct = 1

   # first, try one fit and plot it
   if (True):
      r = test_fitting(0.95, 1, sample_ct)
      plt.axhline(y=90)
      plt.scatter(*zip(*r['all_xys']), s=5, color='b', marker='.')
      plt.scatter(*zip(*r['g'].means_), s=40, color='r', marker='s')
      plt.scatter(*zip(*[s[0].coords for s in r['g'].samples]),
                  s=5, color='g', marker='.')
      for polygon in r['g'].pred_region:
         (xs, ys) = zip(*polygon[0].coords)
         plt.fill(xs, ys, 'k', lw=2, fill=False, edgecolor='r')
      plt.show()
      return

   # next, try a bunch of fits and report how well calibrated they are
   all_ = dict()
   for coverage in (0.50, 0.90, 0.95):
      l.info('COVERAGE = %g' % (coverage))
      all_[coverage] = list()
      for seed in xrange(test_ct):
         l.info('SEED = %d' % (seed))
         all_[coverage].append(test_fitting(coverage, seed, sample_ct))
   l.info('RESULTS')
   for (coverage, results) in all_.iteritems():
      l.info('coverage = %g' % (coverage))
      l.info('  mean observed coverage (covers) = %g'
             % (np.mean([r['coverage_obs'] for r in results])))
      l.info('  MCE (covers) = %g'
             % (np.mean([r['coverage_error'] for r in results])))
      l.info('  mean fudge = %g'
             % (np.mean([r['coverage_fudge'] for r in results])))
      l.info('  mean observed coverage (coverst) = %g'
             % (np.mean([r['coveraget_obs'] for r in results])))
      l.info('  MCE (coverst) = %g'
             % (np.mean([r['coveraget_error'] for r in results])))
      l.info('  mean fudge (coverst) = %g'
             % (np.mean([r['coveraget_fudge'] for r in results])))
      l.info('  mean contour = %g'
             % (np.mean([r['contour'] for r in results])))
      l.info('  mean MSAE = %g km'
             % (np.mean([r['msae'] for r in results])))
      l.info('  mean MCAE = %g km'
             % (np.mean([r['mcae'] for r in results])))
      l.info('  MPRA = %g km^2'
             % (np.mean([r['pra'] for r in results])))

def test_fitting(coverage, seed, sample_ct):
   result = {}
   rs = np.random.RandomState(seed)
   Model.parms_init({ 'mc_sample_ct': sample_ct })  # FIXME: kludge ugly here

   # Create and fit a GMM. We fit random points centered on Alert, Nunavut (83
   # degrees north) as well as Los Alamos in order to test clamping for sampled
   # points that are too far north. The two places are roughly 5,447 km apart.
   ct = sample_ct
   alert_xys = zip(-62.33 + rs.normal(scale=4.0, size=ct*1.5),
                    82.50 + rs.normal(scale=8.0, size=ct*1.5))
   # make sure we are indeed slushing over the northern boundary of the world
   assert (len(filter(lambda xy: xy[1] >= 90, alert_xys)) > 8)
   la_xys = zip(-106.30 + rs.normal(scale=3.0, size=ct),
                 35.89 + rs.normal(scale=2.0, size=ct))
   all_xys = alert_xys + la_xys
   inbounds_xys = filter(lambda xy: xy[1] < 90, all_xys)
   l.info('true points in bounds = %d/%d = %g'
          % (len(inbounds_xys), len(all_xys), len(inbounds_xys)/len(all_xys)))
   result['all_xys'] = all_xys
   result['inbounds_xys'] = inbounds_xys
   all_mp = geos.MultiPoint([geos.Point(xy) for xy in all_xys],
                            srid=srs.SRID_WGS84)

   t1 = time.time()
   g = Geo_GMM.from_fit(all_mp, 2)
   result['g'] = g
   l.info('fitted %d components in %gs' % (len(g.weights_), time.time() - t1))

   t1 = time.time()
   g.prepare(coverage)
   l.info("prepare()'d %d points in %gs" % (len(g.samples), time.time() - t1))

   l.info('component weights: %s' % ([g.weights_],))
   l.info('component assignments: %s'
          % ([len([i for i in g.samples if i[2]==0]),
              len([i for i in g.samples if i[2]==1])],))

   # coverage
   covers_ct = sum(g.covers_p(geos.Point(xy, srid=srs.SRID_WGS84))
                   for xy in inbounds_xys)
   result['coverage_req'] = coverage
   result['coverage_obs'] = covers_ct / len(inbounds_xys)
   result['coverage_error'] = result['coverage_obs'] - coverage
   result['coverage_fudge'] = coverage / result['coverage_obs']
   l.info('observed coverage (in-bounds) = %d/%d = %g'
          % (covers_ct, len(inbounds_xys), result['coverage_obs']))

   t1 = time.time()
   result['contour'] = sum(g.contour(geos.Point(xy, srid=srs.SRID_WGS84))
                           for xy in inbounds_xys) / len(inbounds_xys)
   l.info('computed contour() in %gs per point'
          % ((time.time() - t1) / len(inbounds_xys)))
   covers_ct = sum(g.coverst_p(geos.Point(xy, srid=srs.SRID_WGS84))
                   for xy in inbounds_xys)
   result['coveraget_obs'] = covers_ct / len(inbounds_xys)
   result['coveraget_error'] = result['coveraget_obs'] - coverage
   result['coveraget_fudge'] = coverage / result['coveraget_obs']
   l.info('observed coverage (in-bounds, coverst) = %d/%d = %g'
          % (covers_ct, len(inbounds_xys), result['coveraget_obs']))

   # absolute error for a random true point
   inb_sample = inbounds_xys[:1]
   t1 = time.time()
   sae = [g.sae(geos.Point(p, srid=srs.SRID_WGS84)) for p in inb_sample]
   l.info('computed SAE in %gs per point'
          % ((time.time() - t1) / len(inb_sample)))
   result['msae'] = np.mean(sae)
   t1 = time.time()
   cae = [g.cae(geos.Point(p, srid=srs.SRID_WGS84)) for p in inb_sample]
   l.info('computed CAE in %gs per point'
          % ((time.time() - t1) / len(inb_sample)))
   result['mcae'] = np.mean(cae)

   # area of confidence region
   result['pra'] = g.pred_area

   return result

def sample_gaussian(rs,offset=0.):
   ''' Return the (mean,covar) of a random 2d gaussian by sampling two scalars
   for the mean from the standard normal distribution, shifting by offset. The
   covariance matrix is fixed to [1,0],[0,1], which is positive semidefinite,
   as required.'''
   return (offset + rs.standard_normal(2),
           [[1.,0.],[0.,1.]])

def sample_points(rs, components, ct):
   ''' Sample ct points from a random gaussian mixture model with the
   specified number of components. An equal number of samples are drawn from
   each component.'''
   sz = ct // components
   samples = np.array([]).reshape(0,2)
   mean = 0
   for i in range(0,components):
      (mean,covar) = sample_gaussian(rs, mean)
      samples = np.append(samples, rs.multivariate_normal(mean, covar, sz), 0)
      mean += 5
   return geos.MultiPoint([geos.Point(*xy) for xy in samples],
                          srid=srs.SRID_WGS84)

def results_dict(coverages, fns):
   'initialize a 2d dict of results'
   results = dict.fromkeys(fns)
   for k in results.iterkeys():
      results[k] = dict.fromkeys(coverages,0)
   return results

def test_error_metrics():
   ''' Generate n random gaussians and fit GMMs. Report metrics at
   various coverage levels and inspect for sanity'''
   rs = np.random.RandomState(1)
   gaussian_sample_ct = 100
   sample_ct = 100
   coverages = [0.5, 0.90, 0.95]
   max_n_components = 4
   test_ct = 50 # only test on some points
   fns = ['covers_p','coverst_p','contour','sae','cae']
   Model.parms_init({ 'mc_sample_ct': sample_ct })
   l.info('testing error metrics...')
   for n_components in range(1,max_n_components):
      results = results_dict(coverages, fns)
      for i in range(0,gaussian_sample_ct):
         points = sample_points(rs, n_components, sample_ct)
         g = Geo_GMM.from_fit(points, n_components)
         for coverage in coverages:
            g.prepare(coverage)
            for fn in fns:
               results[fn][coverage] += np.mean(
                  [getattr(g, fn)(p) for p in points[0:test_ct]])
      l.info('#components=%d' % n_components)
      for coverage in coverages:
         l.info('\tcoverage=%g' % coverage)
         for f in fns:
            l.info('\t\tmean %s=%g' % (f,
                                       results[f][coverage] /
                                       gaussian_sample_ct))
