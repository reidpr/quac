'Convenience methods to wrap APSW SQLite databases.'

# Copyright (c) Los Alamos National Security, LLC, and others.

# Note on execute() vs. executemany(): The standard Python DB-API cursors
# offer both execute() and executemany() methods. The latter is often billed
# as a performance improvement, because it saves the overhead of parsing the
# query each time. However, in my testing there is minimal advantage gained by
# executemany() in APSW. This is nice because plain execute() is often easier
# to deal with.
#
# Results of three quick tests against an in-memory database:
#
# execute(), with statement cache:     620k inserts/second
# execute(), without statement cache:  190k
# executemany():                       660k
#
# I suspect this is due to two factors. First, sqlite3 has a
# transaction-per-statement model by default, and executemany() implicitly
# runs in a transaction; if you are using explicit transactions, as we do,
# this advantage goes away. Second, APSW has a prepared statement cache, so
# the savings of preparing only once in executemany goes away as well.
#
# Tests used:
#
# $ python -m timeit -s 'import apsw; db = apsw.Connection(":memory:"); c = db.cursor(); c.execute("create table foo (a int)");' 'c.execute("BEGIN"); [c.execute("insert into foo values (?)", (i,)) for i in range(10000)]; c.execute("COMMIT")'
# 100 loops, best of 3: 16.1 msec per loop
# $ python -m timeit -s 'import apsw; db = apsw.Connection(":memory:", statementcachesize=0); c = db.cursor(); c.execute("create table foo (a int)");' 'c.execute("BEGIN"); [c.execute("insert into foo values (?)", (i,)) for i in range(10000)]; c.execute("COMMIT")'
# 10 loops, best of 3: 51.6 msec per loop
# $ python -m timeit -s 'import apsw; db = apsw.Connection(":memory:"); c = db.cursor(); c.execute("create table foo (a int)");' 'c.execute("BEGIN"); c.executemany("insert into foo values (?)", ((i,) for i in range(10000))); c.execute("COMMIT")'
# 100 loops, best of 3: 15.2 msec per loop

import sys

import apsw


class Not_Enough_Rows_Error(Exception): pass
class Too_Many_Rows_Error(Exception): pass


class SQLite(object):

   __slots__ = ('db',
                'curs')

   def __init__(self, filename, writeable):
      if (writeable):
         flags = apsw.SQLITE_OPEN_READWRITE | apsw.SQLITE_OPEN_CREATE
      else:
         flags = apsw.SQLITE_OPEN_READONLY
      self.db = apsw.Connection(filename, flags=flags)
      self.curs = self.db.cursor()

   def begin(self):
      self.sql("BEGIN IMMEDIATE")

   def close(self):
      # APSW docs suggest that closing the database is unnecessary, but it
      # seems tidier to me. See:
      # http://rogerbinns.github.io/apsw/connection.html#apsw.Connection.close
      self.db.close()

   def commit(self):
      self.sql("COMMIT")

   def exists(self, table, where_clause):
      return (next(self.get("SELECT count(*) FROM %s WHERE %s"
                            % (table, where_clause)))[0] > 0)

   def get(self, sql_, bindvals=None):
      return self.curs.execute(sql_, bindvals)

   def get_many(self, sql_, bindvals=None):
      return self.curs.executemany(sql_, bindvals)

   def get_one(self, sql_, bindvals=None):
      '''Return the single row result of query as an iterable. If row does not
         exist, return KeyError. If multiple rows are returned, raise
         ValueError.'''
      it = self.curs.execute(sql_, bindvals)
      try:
         r = next(it)
      except StopIteration:
         raise Not_Enough_Rows_Error('no such row') from None
      try:
         next(it)
      except StopIteration:
         pass
      else:
         raise Too_Many_Rows_Error('query returned more than one result')
      return r

   def rollback(self):
      self.sql("ROLLBACK")

   def sql(self, sql_, bindvals=None):
      'Execute SQL statement and discard the results.'
      all(self.get(sql_, bindvals))

   def sql_many(self, sql_, bindvals=None):
      all(self.get_many(sql_, bindvals))

   def vacuum(self):
      sql.SQL("VACUUM")
