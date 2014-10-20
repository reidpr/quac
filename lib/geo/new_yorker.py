'''This model estimates that all tweets are from New York City, except
   sometimes it returns None. Good for testing (see base.py docstring for
   sample usage).'''

# Copyright (c) Los Alamos National Security, LLC, and others.

from django.contrib.gis import geos

import u

from . import base
from . import srs


# Two noops for model parameter testing.
def foo(): pass
def bar(): pass


class Location_Estimate(base.Location_Estimate):

   def __init__(self, *args, **kwargs):
      self.point = kwargs['point']
      u.call_kw(base.Location_Estimate.__init__, self, **kwargs)

   def cae(self, pt):
      'No underlying probability model, so cheat and return SAE.'
      return self.sae(pt)

   def populate_best_point(self):
      self.best_point = srs.transform(self.point[1], self.srid)

   def populate_pred_region_real(self):
      self.pred_region = srs.transform(self.point[0], self.srid)


class Model(base.Model):

   parms_default = u.copyupdate(base.Model.parms_default,
                                { 'fail_interval': 7,
                                  'do_nothing_func': foo })

   def build(self):
      self.warn_if_parallel()
      UTM_18N = 32618  # work in UTM for sane units (meters) on buffering
      manhattan = geos.Point((584939, 4509087), srid=UTM_18N)
      manhattan_poly = manhattan.buffer(9500)
      brooklyn_poly = geos.Point((588618, 4497627), srid=UTM_18N).buffer(5000)
      bronx_poly = geos.Point((593911, 4521284), srid=UTM_18N).buffer(2000)
      queens_poly = geos.Point((595675, 4511623), srid=UTM_18N).buffer(1000)

      multiregion = geos.MultiPolygon((manhattan_poly,
                                       brooklyn_poly,
                                       bronx_poly,
                                       queens_poly), srid=manhattan_poly.srid)
      self.pred_region = multiregion.cascaded_union
      self.best_point = manhattan

   def locate(self, tokens, coverage):
      if (self.parms['fail_interval'] > 0
          and u.rand.random() < 1.0/self.parms['fail_interval']):
         return None
      else:
         le = Location_Estimate(point=(self.pred_region, self.best_point),
                                srid=self.srid)
         le.prepare(coverage)
         return le

