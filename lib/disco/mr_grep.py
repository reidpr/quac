# FIXME: stream output into DDFS

'Functions to search tweets for a regular expression.'

# Copyright (c) Los Alamos National Security, LLC, and others.

import collections
import re

import mr_path
mr_path.fix_pythonpath()

import disco.util

import mr_base
import time_
import u


class Job(mr_base.Job, mr_base.TSV_Reader_Job):

   def __init__(self, args, **kw):
      super(Job, self).__init__(args, **kw)
      self.regex = re.compile(args.regex)
      self.add_check_out_tags(':summary', ':matches')

   def map(self, t, params):
      if (self.regex.search(t[2])):
         yield t[1][:10], t  # day, tuple

   def reduce(self, it, out, params):
      # build totals and lists of matches
      match_buf = u.StringIO()
      day_counts = collections.Counter()
      for (day, matches) in disco.util.kvgroup(it):
         matches = list(matches)
         day_counts[day] = len(matches)
         for t in matches:
            match_buf.write('\t'.join(t) + '\n')
      self.check_out_tags()
      # save to ddfs
      summary_buf = u.StringIO()
      for day in time_.dateseq_str(min(day_counts), max(day_counts)):
         summary_buf.write('%s\t%d\n' % (day, day_counts[day]))
      summary_buf.seek(0)
      self.fs.push('%s:summary' % (self.name), ((summary_buf, 'a'),))
      match_buf.seek(0)
      self.fs.push('%s:matches' % (self.name), ((match_buf.buffer, 'a'),))

