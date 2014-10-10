# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

from django.contrib.gis import geos
import numpy as np
import scipy.stats.kde as kde

from . import base
from . import pipeline
import u

l = u.l


def transpose(x):
   return np.array(x).T.tolist()

def build_token_location_map_transpose(token_iterator):
   allpoints = [[],[]]
   tokens = {}
   for (token, points) in token_iterator:
      assert (points.geom_type == 'MultiPoint')
      points_t = transpose(points)
      allpoints[0].extend(points_t[0])
      allpoints[1].extend(points_t[1])            
      tokens[token] = points_t
   return [tokens,allpoints]


class Location_Estimate(base.Location_Estimate):
      def __init__(self, model, confidence, points, tw):
         self.model = model
         self.best_point = max([p for p in transpose(points)], 
                               key=lambda w: model.evaluate(w))
         self.confidence = confidence  
         self.best_point = geos.Point(self.best_point[0],
                                      self.best_point[1], srid=tw.geom.srid)
         poly = self.best_point.buffer(5000)
         self.multiregion = geos.MultiPolygon((poly), srid=poly.srid)
         l.debug('KDE predicts %f,%f' % (self.best_point[0], self.best_point[1]))

      @property
      def point(self):
         return self.best_point

      @property
      def cregion(self):
         return self.multiregion
      
      def likelihood_point(self, pt):
         return self.model.evaluate(pt)


class Message(base.Model):
   '''For a new message, lookup all locations for all tokens it contains. Fit
      a kernel density estimator to this data, and return the location that
      has the maximum value under this estimate'''

   def __init__(self, token_iterator, tokenizer):
      self.tokens = {}  # token, GMM mapping
      base.Model.__init__(self, token_iterator, tokenizer)

   def build(self):
      'Just store all token/location pairs'
      self.tokens = build_token_location_map_transpose(self.token_iterator)[0]

   def locate(self, tw, confidence):      
      tweet_points = [[],[]]
      for token in self.tokenizer.tokenize(tw.text):
         if token in self.tokens:
            tweet_points[0].extend(self.tokens[token][0])
            tweet_points[1].extend(self.tokens[token][1])
      if len(tweet_points[0]) == 0:
         return None
      else:
         model = kde.gaussian_kde(tweet_points)
         return Location_Estimate(model, confidence, tweet_points, tw)


class All_Tweets(base.Model):

   def __init__(self, token_iterator, tokenizer):
      base.Model.__init__(self, token_iterator, tokenizer)

   def build(self):
      self.allpoints = build_token_location_map_transpose(self.token_iterator)[1]
      l.debug('fitting kernel density estimate to %d points...' % 
              len(self.token_iterator))
      t1 = time.time()
      self.global_model = kde.gaussian_kde(self.allpoints)      
      l.debug('...finished in %0.3f s.' % (time.time() - t1))
 
   def locate(self, tw, confidence):      
      return Location_Estimate(self.global_model, 
                               confidence, self.allpoints, tw)


class Message_All_Pipeline(pipeline.Model):
   def __init__(self, token_iterator, tokenizer):
      pipeline.Model.__init__(self, token_iterator, tokenizer, 
                              [Message(token_iterator, tokenizer),
                               All_Tweets(token_iterator, tokenizer)])

