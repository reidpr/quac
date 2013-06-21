# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.


from . import base

class Tweet_Job(base.TSV_Input_Job, base.KV_Pickle_Seq_Output_Job):

   def map(self, fields):
      yield (1,1)

   def reduce(self, ngram, dates):
      yield (1, 'hello')
