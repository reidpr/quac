'''
This file wraps db_glue to offer a simpler interface. The basic abstraction is
that each database handle contains a set of objects of a single type.

The type to be stored needs to implement a few housekeeping methods.
'''

import collections

import db_glue


TABLE = 'data'


class DB_Dict(collections.defaultdict):
   '''A lazy-loading dictionary of databases. Essentially:

      >>> d = DB_Dict('/tmp/foo', Foo_Type)
      >>> d['bar'].insert(...)

      In the second line, if d['bar'] isn't already a database, it will
      magically become one (stored in "/tmp/foo_bar.db").'''

   def __init__(self, prefix, type_):
      self.prefix = prefix
      self.type_ = type_

   def __missing__(self, key):
      self[key] = DB(self.prefix + key, self.type_)
      return self[key]

   def commit(self):
      for db_ in self.itervalues():
         db_.commit()
         

class DB(object):

   __slots__ = ('_db',
                'type_')

   def __init__(self, filename, type_):
      '''Open a database at filename (plus ".db") to store objects of type
         type_, creating a new database if one does not already exist.'''
      self.type_ = type_
      self._open(filename + '.db', self.type_)
      # FIXME: verify table has correct schema, not just present
      if (not self._db.table_exists_p(TABLE)):
         self._db.create_table(TABLE, self.type_.db_cols)
         self.commit()

   def commit(self):
      self._db.commit()

   def delete(self):
      assert False, 'FIXME: unimplemented'
   
   def exists(self, pk_value):
      # We could add LIMIT 1, but since it's a PK, no need.
      sql_ = ("SELECT 1 FROM %s WHERE %s = ?" % (TABLE, self.type_.pk_col))
      return (len(self.sql(sql_, (pk_value,))) > 0)

   def insert(self, item):
      'WARNING: This clobbers existing rows with the same PK.'
      self._db.insert_clobber(TABLE, item.as_dict())

   def rollback(self):
      self._db.rollback()

   def sql(self, sql_, parms=()):
      return self._db.sql(sql_, parms)

   def _open(self, filename, type_):
      self._db = db_glue.DB(filename)

