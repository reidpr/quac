'''This module offers a simple interface to the TSV files we want to store.

   You will note that it doesn't use the csv module. This is because that
   module has a number of annoying habits, the most significant one being that
   it completely does not support unicode. (There are wrappers which solve
   this, but I'd prefer to keep dependencies, particularly those that don't
   come with the OS, to a minimum.) However, the final straw was the fact that
   it wanted to escape quote characters even though I specified no quoting.

   It's really a very simple format. We'll be OK.

   WARNING: Keep the TSV dialect consistent with README.

   See http://docs.python.org/library/io.html for the meaning of the buffering
   parameter. '''

import collections
import io


class Reader(object):

   '''Read rows are returned as lists. Empty strings are converted to None.
      Converting to numbers, etc., is the responsibility of the caller.'''

   __slots__ = ('filename', 'fp')

   def __init__(self, filename, buffering=-1):
      '''Open a TSV file for reading and return the reader object. If the file
         does not exist, raise an exception.'''
      self.filename = filename
      self.fp = io.open(self.filename, mode='rt', buffering=buffering,
                        encoding='utf8')

   def __iter__(self):
      return self

   def close(self):
      self.fp.close()

   def next(self):
      line = self.fp.readline()
      line = line.rstrip('\n')
      if (line == ''):
         raise StopIteration
      return [(col if col != '' else None) for col in line.split('\t')]


class Writer(object):

   __slots__ = ('filename', 'fp')

   def __init__(self, filename=None, fp=None, buffering=-1, clobber=False):
      '''Open a TSV file for writing and return the writer object, creating a
         new file if one does not already exist. If clobber is True, overwrite
         any existing contents, if False (the default), append.'''
      self.filename = filename
      mode = 'wt' if clobber else 'at'
      if (fp is not None):
         self.fp = fp
      else:
         self.fp = io.open(self.filename, mode=mode, buffering=buffering,
                           encoding='utf8')

   def close(self):
      self.fp.close()

   def writerow(self, row):
      def _unicodify(s):
         if s is None:
            return u''
         elif isinstance(s, unicode):
            return s
         else:
            return unicode(s)
      self.fp.write('\t'.join([_unicodify(i) for i in row]) + '\n')


class Writer_Unicode(object):

   '''An abuse of the module. This class is simply a writer of raw unicode
      lines, with nothing to do with TSV.'''

   def __init__(self, filename=None, buffering=-1, clobber=False):
      '''Open a unicode text file for writing and return the writer object,
         creating a new file if one does not already exist. If clobber is
         True, overwrite any existing contents, if False (the default),
         append.'''
      self.filename = filename
      mode = 'wt' if clobber else 'at'
      self.fp = io.open(self.filename, mode=mode, buffering=buffering,
                        encoding='utf8')

   def close(self):
      self.fp.close()

   def write(self, x):
      self.fp.write(x)


class Dict(collections.defaultdict):
   '''A lazy-loading dictionary of open TSV files. Essentially:

      >>> t = tsv_glue.Dict('/tmp/foo_')
      >>> d['bar'].writerow([1,2,3])

      In the second line, if t['bar'] isn't already an open TSV file, it will
      magically become one (stored in "/tmp/foo_bar.tsv").'''

   def __init__(self, prefix, class_=Writer, buffering=-1):
      self.prefix = prefix
      self.class_ = class_
      self.buffering = buffering

   def __missing__(self, key):
      self[key] = self.class_(filename=self.filename_from_key(key),
                              buffering=self.buffering)
      return self[key]

   def close(self):
      for f in self.itervalues():
         f.close()

   def filename_from_key(self, key):
      return (self.prefix + key + '.tsv')

   def iterfiles(self):
      return [self.filename_from_key(i) for i in self.iterkeys()]

