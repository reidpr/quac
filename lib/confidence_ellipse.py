'''This module contains functions to compute confidence ellipses for
   2-dimensional Gaussians and Gaussian mixture models. (Note that by
   "ellipse" we mean "polygon approximating an ellipse".) See
   <http://sites.stat.psu.edu/~ajw13/stat505/fa06/06_multnorm/06_multnorm_revist.html>.'''

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.



import math
import numpy as np

from django.contrib.gis import geos
import planar


# Number of edges in the polygons which approximate an ellipse. This should be
# divisible by 4, which places a polygon vertex at each ellipse vertex.
POLYGON_EDGES = 32


class My_Polygon(planar.Polygon):
   'Knows how to convert itself to a geos.Polygon.'

   @property
   def as_geos(self):
      # Two basic tricks here:
      # 1. planar.Polygon is sort of like a sequence of sequences, but not
      #    quite enough apparently.
      # 2. geos.Polygon requires a closed ring (i.e., a[0] == a[-1]).
      return geos.Polygon([tuple(i) for i in self] + [tuple(self[0])])


def chisq_crit2(confidence):
   '''Return the critical value of a chi-squared distribution with 2 degrees
      of freedom at a given confidence level (e.g., 0.95).'''
   # Typically, you would look this up in a table, but it's easy to compute
   # when DOF = 2.
   return (-2 * math.log(1 - confidence))

def ellipse_1(mean, covar, confidence):
   '''Return an ellipse of the given confidence for the given Gaussian.'''
   # Draw a circle of radius 1 around the origin.
   cir = My_Polygon.regular(POLYGON_EDGES, radius=1)
   # Compute ellipse parameters.
   (eivals, eivecs) = np.linalg.eigh(covar)
   crit = chisq_crit2(confidence)
   scale0 = math.sqrt(crit * eivals[0])
   scale1 = math.sqrt(crit * eivals[1])
   angle = planar.Vec2(eivecs[0][0], eivecs[0][1]).angle
   # Transform the circle into an ellipse. NOTE: Originally, I set this up to
   # build a full transformation matrix and then multiply the polygon by that
   # composite matrix. However, the order of operations was really wierd --
   # e.g., t * s * r works, even though the transformation order is s, r, t. I
   # think this is due to some mismatch between the associativity of the
   # multiplication operator and calls to the __mult__() special method.
   # Anyway, this way is a lot easier to follow.
   return (planar.Affine.translation(mean)
           * (planar.Affine.rotation(angle)
              * (planar.Affine.scale((scale0, scale1)) * cir))).as_geos

def ellipses_n(gmm, confidence):
   '''Return a (perhaps noncontiguous) confidence region for the given mixture
      model at the given confidence. To do this, we compute the union of the
      confidence ellipses for each component. Thus, the confidence of a given
      component region is *not* proportional to its area.'''
   # FIXME: need to consider weight of each component!
   assert False, 'untested'
   ells = []
   for i in range(gmm.n_components):
      ells.append(ellipse_1(gmm.means_[i], gmm.covars_[i], confidence))
   return geos.MultiPolygon(ells).cascaded_union


# If run as a script, do a simple test.
if (__name__ == '__main__'):
   import matplotlib.pyplot as plt
   import sklearn.mixture
   data = [(0,0), (1,0), (1,1), (1,2), (2,2), (2,3)]
   gmm = sklearn.mixture.GMM(1, 'full')
   gmm.fit(data)
   mean = gmm.means_[0]
   covar = gmm.covars_[0]
   fig = plt.figure(1)
   plt.axis('equal')
   plt.scatter([i[0] for i in data], [i[1] for i in data])
   points95 = ellipse_1(mean, covar, 0.95).coords[0]
   plt.scatter([i[0] for i in points95], [i[1] for i in points95], c='red')
   points99 = ellipse_1(mean, covar, 0.99).coords[0]
   plt.scatter([i[0] for i in points99], [i[1] for i in points99], c='green')
   plt.show()
