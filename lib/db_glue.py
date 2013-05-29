# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others. This
# file is based on db_glue.py from Cyclopath. Therefore, portions are
# copyright (c) 2006-2010 Regents of the University of Minnesota.
#
# FIXME: Columns containing geodata must end in "geom", and other columns
# mustn't. Why? SpatiaLite has some severe brain damage in that it isn't
# willing to automatically convert geometry columns to and from strings.
# Therefore, we have to screw around to add the relevant function calls
# ourselves. See DB.insert() and DB.select() for the voodoo (and note that you
# cannot use DB.sql() to fetch geometries).


import os

from pysqlite2 import dbapi2 as sqlite3  # has loadable extensions
from django.contrib.gis import geos

import testable
import time_
import u


# FIXME: Not sure exactly where this searches...
SPATIALITE_PATH = 'libspatialite.so'


### Geometry adapters ###

# FIXME: These do string/geometry converstion, but that's not enough: also
# need to make function calls. See above.

def geometry_adapt(g):
   return g.wkt  # FIXME: change to EWKT when SpatiaLite supports it
sqlite3.register_adapter(geos.Point, geometry_adapt)

def geometry_convert(ewkt):
   return geos.GEOSGeometry(ewkt)
sqlite3.register_converter('geom', geometry_convert)
sqlite3.register_converter('geometry', geometry_convert)


### Other adapters ###

def datetime_convert(s):
   # FIXME: This is here because the built-in datetime adapter is too stupid
   # to parse timestamps with a time zone. Remove when brain damage is gone.
   #
   # FIXME: The datetimes returned by isodate can't be pickled (see more
   # detailed note in time_.py). Because we're not actually storing anything
   # other than UTC in the database, for now use a simpler parsing function
   # that gives results that really can be pickled.
   #return time_.iso8601_parse(s)
   return time_.iso8601utc_parse(s)
sqlite3.register_converter('timestamp', datetime_convert)


### Database handle class ###

class No_Such_Database(Exception):
   pass


class DB(object):

   __slots__ = ('conn',
                'curs')  # only cursors have the description attribute

   def __init__(self, filename, create=False, speedy=True, spatialite=True):
      if (not create and not os.path.isfile(filename)):
         raise No_Such_Database("%s does not exist and create==False"
                                % (filename))
      # see http://www.sqlite.org/lang_transaction.html
      self.conn = sqlite3.connect(filename, isolation_level='DEFERRED',
                                  detect_types=(sqlite3.PARSE_DECLTYPES
                                                |sqlite3.PARSE_COLNAMES))
      self.conn.row_factory = sqlite3.Row  # FIXME: interacts badly with joblib
      if (spatialite):
         self.conn.enable_load_extension(True)
         # FIXME: SpatiaLite prints garbage to stdout. Remove this workaround
         # when SpatiaLite becomes less stupid (3.0.1?).
         u.stdout_silence()
         self.conn.load_extension(SPATIALITE_PATH)
         u.stdout_restore()
      self.curs = self.conn.cursor()
      # FIXME: this breaks AddGeometryColumn()...
      #self.sql("PRAGMA foreign_keys = ON")  # why is this not the default?
      if (speedy):
         self.sql("PRAGMA synchronous = OFF")  # faster but a little riskier

   def commit(self):
      self.conn.commit()

   def create_table(self, name, cols):
      '''Create a table named name, with columns listed in cols (a mapping of
         name,type pairs).'''
      s = ("CREATE TABLE %s (%s)"
           % (name,
              ", ".join(["%s %s" % (k, v) for (k, v) in cols.iteritems()])))
      self.sql(s)

   def delete(self, table, id_cols):
      assert False, 'FIXME: needs update for SQLite'
      self.sql("DELETE FROM %s WHERE %s"
               % (table, " AND ".join(map(lambda x: "%s = %%(%s)s" % (x, x),
                                          id_cols.keys()))),
               id_cols)

   def dict_prep(self, d):
      'Some values need transformation before storage; this function does it.'
      # FIXME: Use a list comprehension, map(), or something else?
      for (k, v) in d.iteritems():
         # Empty string becomes None
         if (v == ''):
            d[k] = None

   def insert(self, table, cols, clobber=False):
      '''Insert a row into table; cols is a mapping of column, value pairs. If
         a row with the same PK already exists, it is overwritten.'''
      # FIXME: Columns ending in "geom" are special. See FIXME at top of file.
      def placeholder(colname):
         if (colname[-4:] == 'geom'):
            return 'GeomFromText(:%s, %d)' % (colname, cols[colname].srid)
         else:
            return ':' + colname
      if (clobber):
         or_replace = 'OR REPLACE'
      else:
         or_replace = ''
      s = ("INSERT %s INTO %s (%s) VALUES (%s)"
           % (or_replace,
              table,
              ", ".join(cols.iterkeys()),
              ", ".join(map(placeholder, cols.iterkeys()))))
      self.sql(s, cols)

   def is_empty(self):
      'Return true if the database is empty, false otherwise.'
      return (self.table_ct() == 0)

   def metadata_get(self, key):
      return self.sql("SELECT value FROM metadata WHERE key=?", (key,))[0][0]

   def metadata_set(self, key, value):
      self.insert('metadata', { 'key': key, 'value': value }, clobber=True)

   def rollback(self):
      self.conn.rollback()

   def select(self, cols, sql_rest, parms=()):
      '''cols is a sequence of (column, alias) pairs. This wrapper is only
         helpful if you need the SpatiaLite workaround voodoo (see above).'''
      # FIXME: This should be removed when SpatiaLite becomes less stupid.
      def wrap_col(name):
         if (name[1].split()[0][-4:] == 'geom'):
            return 'AsEWKT(%s) AS %s' % (name[0], name[1])
         else:
            return '%s AS %s' % (name[0], name[1])
      col_sql = ', '.join(map(wrap_col, cols))
      return self.sql("SELECT %s %s" % (col_sql, sql_rest), parms)

   def sql(self, sql, parms=()):
      self.curs.execute(sql, parms)
      if (self.curs.description is None):
         # no results from this query
         return None
      else:
         return self.curs.fetchall()

   def table_exists_p(self, table):
      return (1 == len(self.sql("""SELECT 1 FROM sqlite_master
                                   WHERE name = ?""", (table,))))

   def table_ct(self):
      'Return the number of tables in the database.'
      return self.sql("SELECT count(*) FROM sqlite_master")[0][0]

testable.register('''

   # FIXME: the kludge to silence SpatiaLite fails with AttributeError when
   # run under doctest. Therefore, we test without SpatiaLite for now.

   # Initialize an in-memory database
   >>> db = DB(':memory:', create=True, spatialite=False)
   >>> db.is_empty()
   True
   >>> db.create_table('foo', { 'a': 'int' })

   # Does table_ct() work?
   >>> db.table_ct()
   1
   >>> db.is_empty()
   False

''')
