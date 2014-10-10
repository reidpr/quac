'Try sub-models in order and return the first estimate that is not None.'

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.


from . import base
import u

# FIXME: won't gmm.model_parms variable break pipeline? (can't have more than one model instance?)
# FIXME: figure out how to pass model_parms for each submodel here
class Model(base.Model):

   # FIXME: change to take a list of classes? Then caller doesn't need to
   # redundantly specify token_iterator and tokenizer.
   def __init__(self, models):
      assert False, 'unimplemented'
      base.Model.__init__(self, None)
      self.submodels = models

   def build(self):
      for m in self.submodels:
         m.build()

   def locate(self, tokens, confidence, srid):
      for m in self.submodels:
         location = m.locate(tokens, confidence, srid)
         if location is not None:
            return location
      return None
