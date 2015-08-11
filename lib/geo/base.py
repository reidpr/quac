'''Base classes for the various location models. Example usage:

   >>> import tweet
   >>> from tok.unicode_props import UP_Tiny
   >>> import geo.new_yorker
   >>> tw = tweet.Tweet.from_list(['186347637706989568',
   ...                             '2012-04-01T07:01:53+00:00',
   ...                             'RT @UberFacts: The human brain can only maintain 150 stable social relationships.',
   ...                             'allybell_',
   ...                             'I am a user description',
   ...                             'en',
   ...                             'Middlesbrough',
   ...                             'London',
   ...                             None,
   ...                             None,
   ...                             None])
   >>> m = geo.new_yorker.Model.parms_init({ 'fail_interval': 0 })
   >>> m = geo.new_yorker.Model([], 4326)  # dummy args
   >>> m.build()
   >>> le = m.locate(tw.tokenize(UP_Tiny(1), ['tx'], True), 0.95)
   >>> le.best_point.coords
   (-73.994..., 40.728...)'''

# Copyright (c) Los Alamos National Security, LLC, and others.

from abc import ABCMeta, abstractmethod
from collections import OrderedDict
import io
import json
import sys

from django.contrib.gis import geos
import numpy as np

import multicore
import testable
import u

from . import srs

l = u.l

# Suppress "RuntimeWarning: overflow encountered in exp", which doesn't
# actually tell us anything, since the result is zero, which is what we want.
np.seterr(over='ignore')


### Constants ###

# Tweet fields we can learn from.
FIELDS = set(('tx', 'ds', 'ln', 'lo', 'tz'))

# some defaults for the geo-images
GEOIMG_LATMIN = srs.LATMIN
GEOIMG_LATMAX = srs.LATMAX
GEOIMG_LONMIN = -179.9999  # weird wraparound effects if we do +/- 180
GEOIMG_LONMAX = 179.9999
GEOIMG_WIDTH = 1024  # y pixel size computed to make "square" pixels


### Classes ###

class Location_Estimate(object, metaclass=ABCMeta):
   '''An estimated location that contains a probability model of some kind.

        srid ........... ID of the SRS for geometries in the estimate.

        pred_region .... A MultiPolygon containing a prediction region of
                         (perhaps approximately) the coverage requested. This
                         region is guaranteed to be within the map (e.g., no
                         coordinates north of 90 degrees).

        pred_coverage .. Coverage (\beta in the paper) of prediction region.

        pred_area ...... Area (km^2) of the prediction region.

        best_point ..... The single Point which is the most probable location.
                         This point is not necessarily within the prediction
                         region!

      Given the true location corresponding to the estimate, objects of this
      class can also compute several metrics for the accuracy, precision, and
      calibration of the estimate. Further details about these are available
      in our publications.'''

   def __init__(self, coverage=None, srid=None):
      self.pred_coverage = coverage
      self.srid = srid
      self.prepared = False
      self.pred_region = None
      self.pred_area = None
      self.best_point = None

   @property
   def explanation(self):
      '''(factor, weight) pairs where factor is some human-readable reason for
         constructing the estimate and weight is the corresponding weight of
         that reason. For example, geo.gmm models populate this with a set of
         (token, weight) pairs.'''
      return {}

   @abstractmethod
   def cae(self, pt):
      'Return the comprehensive absolute error for true Point pt.'

   def contour(self, pt):
      '''Return the contour value [0, 1] on which pt lies. Some subclasses
         cannot implement this method, in which case they return -1.'''
      return -1

   def covers_p(self, pt):
      '''Return True if point pt is covered by the prediction region, False
         otherwise. Do this test by actually testing whether the point is
         within the prediction region.'''
      assert (pt.geom_type == 'Point')
      assert (pt.srid == self.srid)
      # NOTE: This contains a weirdness in that p is not actually within
      # self.pred_region if it's on the boundary. Really what we want is
      # "Covers", but GeoDjango doesn't seem to offer that.
      return self.pred_region.contains(pt)

   def coverst_p(self, pt):
      '''Return True if point pt is covered by the prediction region, False
         otherwise. Subclasses may (but are not required to) accomplish this
         test by some method which does not actually test against the
         prediction region (because it's more accurate, faster, etc.).'''
      assert (pt.geom_type == 'Point')
      assert (pt.srid == self.srid)
      return self.coverst_p_real(pt)

   def coverst_p_real(self, pt):
      return self.covers_p(pt)

   def dump_geofiles(self, basename, width_px, coverage=None):
      '''Dump files containing this estimate's prediction region and (for some
         subclasses) model.'''
      if (coverage is not None):
         # may not actually need to prepare; this is a bit of a hack
         self.prepare(coverage)
      srs.dump_geojson(basename + '.pr', self.pred_region)
      self.dump_geoimage(basename, width_px)

   def dump_geoimage(self, basename, width_px):
      '''Dump a georeferenced image of this estimate to a file with the given
         basename (i.e., an appropriate extension such as .tiff is added) and
         width (height is automatically calculated). For some subclasses, this
         is a no-op.'''
      pass

   #@abstractmethod
   def likelihood_polygon(self, pg):
      'Return the probability that the true point is covered by Polygon pg.'
      assert False, 'unimplemented'

   @abstractmethod
   def populate_best_point(self):
      'Compute the best point and put the result in self.best_point.'

   def populate_pred_area(self):
      'Compute the area of the prediction region and set self.pred_area.'
      self.pred_area = srs.geodesic_area(self.pred_region)

   def populate_pred_region(self, coverage):
      '''Given coverage, which may be different than self.coverage, compute a
         prediction region for that coverage and assign it to
         self.pred_region. Also, compute self.pred_area accordingly. Users of
         the location estimate can call this method multiple times to generate
         new prediction regions for different coverages.

         Note: subclasses should override populate_pred_region_real(), not
         this method.'''
      assert (0 < coverage < 1)
      self.pred_coverage = coverage
      self.populate_pred_region_real()
      self.populate_pred_area()

   @abstractmethod
   def populate_pred_region_real(self):
      '''Compute the prediction region that corresponds to self.pred_coverage
         and assign it to self.pred_region.'''

   def prepare(self, coverage=None):
      '''Some subclasses need to use Monte Carlo methods or other expensive
         techniques to prepare the estimate. This method performs those
         operations; until it is called, the estimate is not usable. It is
         available in order that callers can separate construction from this
         (potentially) costly operation; however, the default behavior of the
         constructor is to call it.

         Note: subclasses should override prepare_real(), not this method.'''
      if (coverage is not None):
         self.pred_coverage = coverage
      self.prepare_real()
      self.populate_best_point()
      self.populate_pred_region(self.pred_coverage)
      self.prepared = True

   def prepare_real(self):
      '''Perform any preparatory steps (that are *independent of coverage*)
         for computing the prediction region and best point.'''
      pass

   def sae(self, pt):
      'Return the simple absolute error (in km) for true Point pt.'
      return srs.geodesic_distance(self.best_point, pt)

   def to_json(self):
      '''Return a GeoJSON representation of the estimate's prediction region
         and best point.'''
      assert False, 'untested'
      return (  '''{ "type": "FeatureCollection",
                     "crs": { "type": "name",
                              "properties": { "name": "EPSG:%d" } },
                     "features": [
                       { "type": "Feature",
                         "properties": { "name": "best_point" },
                         "geometry": %s },
                       { "type": "Feature",
                         "properties": { "name": "pred_region",
                                         "coverage": %g },
                         "geometry": %s }
                     ] }''' % (self.srid,
                               self.best_point.json,
                               self.pred_coverage,
                               self.pred_region.json))

   def unprepare(self):
      '''Often, prepare() generates a bunch of date (e.g., samples). This
         method throws those data away, making the estimate useless but saving
         memory. (Some things might still work, but rely on such behavior at
         your own risk.) Calling prepare() again (e.g., after a pickle and
         unpickle) restores the situation.'''
      self.prepared = False


class Model(object, metaclass=ABCMeta):
   '''Base class for geometric models.'''

   parms_default = { 'mc_sample_ct': 1000 }
   parms = None

   def __init__(self, tokens, srid, tweets=None):
      '''tokens is an iterator of tuples, each containing a token and a
         MultiPoint containing all the points associated with that token. The
         iterator will be completely consumed upon construction. The model
         will process everything; it is the caller's responsibility to filter
         out tokens and/or points that should not be considered.

         tweets is a sequence of tweet objects. The set of tweets used to
         construct tokens and the tweets in tweets may be the same,
         overlapping, or distinct.'''
      self.srid = srid
      self.tokens = dict(tokens)
      self.tweets = tweets
      if (self.parms is None):
         self.parms_init({})

   @property
   def token_summary_keys(self):
      'List of keys for self.token_summary for an arbitrary token.'
      return iter(self.token_summary(next(iter(self.tokens.keys()))).keys())

   @classmethod
   def parms_init(class_, parms, log_parms=False):
      '''Initialize the model parameters with parms. If any parameters remain
         with a value of None, or if anything in parms is not also in the
         default parameters, raise ValueError. WARNING: Of course, you can't
         have multiple instances of the same class with different parameters
         in the same process.'''
      parms = parms.copy()
      # check for bogus parameters
      for k in parms.keys():
         if (k not in class_.parms_default):
            raise ValueError('parameter %s is not supported' % (k))
      # munge in functions, if they exist
      for (k, v) in parms.items():
         if (isinstance(v, str)):
            try:
               parms[k] = getattr(sys.modules[class_.__module__], v)
            except AttributeError:
               pass
      # update parms class attribute
      class_.parms = u.copyupdate(class_.parms_default, parms)
      # print a report
      if (log_parms):
         l.info('model parameters:')
         # note: spacing matches model_test.Test_Sequence.main()
         for (k,v) in sorted(class_.parms.items()):
            l.info('  %s: %*s %s' % (k, 19 - len(k), ' ', str(v)))
      # check for missing parameters
      if (None in iter(class_.parms.values())):
         raise ValueError('model parameter with value None')

   @abstractmethod
   def build(self):
      'Actually compute the model. This method can take a long time.'

   def dump_geofiles(self, basename, geoimage_width, token):
      'Write geofiles to files with basename basename for given token.'
      srs.dump_geojson(basename + '.points', self.tokens[token])
      # FIXME: awkward to prepare() here.
      if (not self.token_gmms[token].prepared):
         self.parms_init({})
         self.token_gmms[token].prepare(0.95)
      self.token_gmms[token].dump_geofiles(basename, geoimage_width)

   @abstractmethod
   def locate(self, tokens, confidence):
      '''Given a sequence of tokens, return a prepare()'d Location_Estimate at
         the given confidence.'''
      # Note: descendants should not specify a default for confidence (this
      # violates DRY). If we decide we want that, we can put it once here and
      # refactor existing locate() into locate_real().

   def token_summary(self, token):
      '''An OrderedDict containing summary parameters for a given token. (Not
         sufficient to reconstruct the model for that token -- this is just a
         human-readable summary.)

         token and point_ct are required and must appear as the first two
         items.'''
      return OrderedDict([('token', token),
                          ('point_ct', len(self.tokens[token]))])

   def warn_if_parallel(self):
      '''Log a warning if multicore.core_ct > 1. Models that can't use
         multiple cores should call this at the beginning of build().'''
      if (multicore.core_ct > 1):
         l.warn('%d cores requested, but %s is serial'
                % (multicore.core_ct, self.__class__))

# Test-Depends: geo
testable.register('')
