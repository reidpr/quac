'This model cheats and returns the true location.'

# Copyright (c) Los Alamos National Security, LLC, and others.


from django.contrib.gis import geos

from . import base


class Model(base.Model):

   class LE(base.Location_Estimate):

      def __init__(self, point, cregion, confidence):
         self.point = point
         self.cregion = cregion
         self.confidence = confidence
         assert (self.point.srid == self.cregion.srid)

      def likelihood_point(self, pt):
         return 0.5

   def build(self):
      pass

   def locate(self, tw, conf=0.95):
      poly = tw.geom.buffer(5000)  # FIXME: change to meters?
      multiregion = geos.MultiPolygon((poly), srid=poly.srid)
      return self.LE(point=tw.geom, cregion=multiregion, confidence=conf)
