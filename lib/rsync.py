# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

import itertools
import os.path
from pprint import pprint
import subprocess

import testable
import u

l = u.l


def byinclude(from_url, dest_dir, bwlimit, includes, verbose=False):
   '''Mirror from the specified URL, including only the patterns specified.
      rsync output, including error messages, goes to stdout. Return value is
      True if the rsync reported successful execution, False otherwise (in
      which case a warning is also logged).'''
   dir_includes = set()
   for i in includes:
      dir_includes.update(leading_dirs(i))
   more_args = list(include_args(dir_includes))
   more_args += include_args(includes)  # include includes
   more_args += ['--exclude', '*']      # exclude everything not included
   return fetch(from_url, dest_dir, bwlimit, more_args, verbose)

def fetch(from_url, dest_dir, bwlimit, more_args, verbose):
   if (from_url is None or len(from_url) <= 1 or from_url[-1] != '/'):
      raise ValueError('URL must end in slash, but "%s" does not' % (from_url))
   assert (os.path.isdir(dest_dir))
   assert (bwlimit > 0)
   rsync = [ 'rsync', from_url, dest_dir,
             '--verbose',     # print which files are being transferred
             '--archive',     # recurse, preserve most metadata
             '--copy-links',  # copy symlink referent instead of link itself
             '--stats',       # more statistics after transfer
             '-h', '-h',      # human-readable numbers, with powers of 2
             '--partial',     # keep partial tranfers for faster restart
             '--partial-dir', '.rsync-tmp',
                              # don't overwrite good files w/ partial transfers
             '--bwlimit=%d' % (bwlimit) ]
   if (verbose):
      rsync += ['--progress']
   rsync += more_args
   l.debug('will call rsync with: %s' % (str(rsync)))
   retval = subprocess.call(rsync, stderr=subprocess.STDOUT)
   if (retval):
      l.warning('rsync invocation failed')
      return False
   else:
      return True

def include_args(includes):
   '''E.g.:

      >>> list(include_args(['a', 'b', 'c']))
      ['--include', 'a', '--include', 'b', '--include', 'c']
      >>> list(include_args(set(['a'])))
      ['--include', 'a']
      >>> list(include_args([]))
      []'''
   return itertools.chain.from_iterable(('--include', i) for i in includes)

def leading_dirs(path):
   '''Return a set containing each directory in absolute path path, except for
      the root directory. For example:

      >>> sorted(leading_dirs('/a/b/c'))
      ['/a', '/a/b']
      >>> pprint(leading_dirs('/a'))
      set()
      >>> leading_dirs('')
      Traceback (most recent call last):
        ...
      ValueError: path must have at least one element
      >>> leading_dirs('/')
      Traceback (most recent call last):
        ...
      ValueError: path must have at least one element
      >>> leading_dirs('//')
      Traceback (most recent call last):
        ...
      ValueError: path // contains adjacent slashes
      >>> leading_dirs('a/b/c')
      Traceback (most recent call last):
        ...
      ValueError: path a/b/c is not absolute'''
   if (len(path) <= 1):
      raise ValueError('path must have at least one element')
   if (path[0] != '/'):
      raise ValueError('path %s is not absolute' % (path))
   if (path.find('//') != -1):
      raise ValueError('path %s contains adjacent slashes' % (path))
   ldirs = set()
   dirs = path.split('/')[1:-1]
   for di in range(len(dirs)):
      ldirs.add('/' + '/'.join(dirs[:di+1]))
   return ldirs


testable.register('')
