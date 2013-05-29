# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

import mr_path
mr_path.fixpythonpath()

import mr_base
import u


class Job(mr_base.Job, mr_base.Tweet_Reader_Job):

   def __init__(self, args, **kw):
      super(Job, self).__init__(args, kw)
      self.tokenizer = # FIXME
      self.add_check_out_tags(args.output)

   def map(self, tw, params):
      # YOU ARE HERE
