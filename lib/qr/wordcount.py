'''Count the number of occurrences of each word in the input. Not very smart;
   mostly useful as example/testing.'''

# Copyright (c) Los Alamos National Security, LLC, and others.


from . import base

class Job(base.Line_Input_Job, base.Line_Output_Job):

   def map(self, line):
      for word in line.split():
         yield (word, None)

   def reduce(self, word, nones):
      yield '%d %s' % (len(list(nones)) * self.params['factor'], word)
