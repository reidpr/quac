'Base classes and stuff for Disco jobs.'

# Copyright (c) Los Alamos National Security, LLC, and others.

import datetime
import io
import os.path
from pprint import pprint

import mr_path
mr_path.fix_pythonpath()

import disco.core
import disco.ddfs

import testable
import u
l = u.l


### Job submission helper function

def run(jobclass, args):
   l.info('starting; args:')
   for (arg, val) in sorted(vars(args).items()):
      l.info('  %-16s %s' % (arg, val))
   job = jobclass(args)
   job.run(input=['tag://' + args.input])
   l.info('started job %s' % (job.name))
   if (args.verbose):
      l.debug('will wait for job to finish')
      job.wait(show='nocolor')
      l.debug('job done')
   for tag in job.out_tags:
      l.info('output tag: %s' % (tag))
   l.info('job submission complete')


### Core job superclass

class Job(disco.core.Job):

   def __init__(self, args, **kw):
      super(Job, self).__init__(**kw)
      self.args = args
      self.name = (self.__module__ + '_'
                   + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
      self.fs = disco.ddfs.DDFS()
      self.out_tags = set()

   def add_check_out_tags(self, *tags):
      self.add_out_tags(*args)
      self.check_out_tags()

   def add_out_tags(self, *tags):
      '''*tags is the list of tags to use; any tag beginning in ``:`` is a
         suffix to be appended to the job name. E.g.:

         >>> j = Job(object())
         >>> j.name = 'doctest_foo'
         >>> j.add_out_tags('doctest_bar', ':baz')
         >>> pprint(j.out_tags)
         ['doctest_bar', 'doctest_foo:baz']'''
      for tag in tags:
         if (tag[0] == ':'):
            self.out_tags.add(self.name + tag)
         else:
            self.out_tags.add(tag)

   def check_out_tags(self):
      '''Raise ValueError if any of the output tags already exist. Note that
         there's a race condition here, so it's nothing more than a sanity
         check.'''
      for tag in self.out_tags:
         if (self.fs.exists(tag)):
            raise ValueError('tag %s already exists' % (tag))

   def run(self, **kw):
      if ('required_modules' in kw):
         raise ValueError('required_modules is not supported by this subclass')
      kw['required_modules'] = [('mr_path', os.path.abspath(mr_path.__file__))]
      super(Job, self).run(**kw)


# Some mixins for various handy behavior.

class TSV_Reader_Job(object):

   @staticmethod
   def map_reader(fp, size, url, params):
      # Note: I can't find this in the docs or the source, but fp is
      # apparently a regular old open file, at least on my one-node tests. I
      # suspect this may be different when nodes start to send each other data
      # over HTTP, but we'll cross that bridge when we come to it.
      fp_unicode = io.open(fp.fileno(), encoding='utf8')
      for line in fp_unicode:
         yield line.split('\t')


# Test-Depends: manual
testable.register('')
