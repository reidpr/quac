# Copyright © Los Alamos National Security, LLC, and others.

import os
from pprint import pprint
import time

import sqlite3
import numpy as np

import u

outer_ct = 10
inner_ct = 100000

u.logging_init('sl', verbose_=True)
l = u.l

#u.memory_use_log()

conn = sqlite3.connect('/data6/foo.db')
db = conn.cursor()
db.execute('PRAGMA cache_size = -1048576')
db.execute('PRAGMA encoding = "UTF-8"')
db.execute('PRAGMA journal_mode = OFF')
db.execute('PRAGMA page_size = 65536')
db.execute('PRAGMA synchronous = OFF')
db.execute('CREATE TABLE ts (namespace TEXT, name TEXT, total INT, data TEXT)')
db.execute('CREATE INDEX ts_idx ON ts (namespace, name)')

start_out = time.time()
for j in range(outer_ct):
   start = time.time()
   db.executemany('INSERT INTO ts VALUES (?, ?, ?, ?)',
                  (('en', str(10 * (j * inner_ct + i)), 8675309,
                    np.ones(720, dtype=np.int32).data)
                   for i in range(inner_ct)))
   conn.commit()
   end = time.time()
   elapsed = end - start
   l.info('inserted %d vectors in %s (%d/s), %d, %.3f'
          % (inner_ct, u.fmt_seconds(elapsed), inner_ct/elapsed,
             (j+1)*inner_ct, (j+1)*inner_ct/(outer_ct*inner_ct)))
   #u.memory_use_log()

os.system('clear-disk-cache')

start_out = time.time()

# for j in range(outer_ct):
#    start = time.time()
#    db.execute('begin')
#    insert = list(range(0, inner_ct, 100))
#    for i in insert:
#       db.execute('UPDATE ts SET total=?, data=? WHERE namespace=? AND name=?',
#                  (1, np.zeros(720, dtype=np.int32).data,
#                   'en', str(10 * (j * inner_ct + i))))
#    conn.commit()
#    end = time.time()
#    elapsed = end - start
#    l.info('updated %d vectors in %s (%d/s), %d, %.3f'
#           % (len(insert), u.fmt_seconds(elapsed), len(insert)/elapsed,
#              (j+1)*inner_ct, (j+1)*inner_ct/(outer_ct*inner_ct)))

start_out = time.time()
for j in range(outer_ct):
   start = time.time()
   insert = list(range(0, inner_ct, 100))
   db.executemany('UPDATE ts SET total=?, data=? WHERE namespace=? AND name=?',
                  ((1, np.zeros(720, dtype=np.int32).data,
                    'en', str(10 * (j * inner_ct + i)))
                   for i in insert))
   conn.commit()
   end = time.time()
   elapsed = end - start
   l.info('updated %d vectors in %s (%d/s), %d, %.3f'
          % (len(insert), u.fmt_seconds(elapsed), len(insert)/elapsed,
             (j+1)*inner_ct, (j+1)*inner_ct/(outer_ct*inner_ct)))

# start_out = time.time()
# for j in range(outer_ct):
#    start = time.time()
#    insert = list(range(0, inner_ct, 10))
#    db.executemany('INSERT INTO ts VALUES (?, ?, ?, ?)',
#                   (('en', str(10 * (j * inner_ct + i) + 1), 8675309,
#                     np.ones(720, dtype=np.int32).data)
#                    for i in insert))
#    conn.commit()
#    end = time.time()
#    elapsed = end - start
#    l.info('added %d vectors in %s (%d/s), %d, %.3f'
#           % (len(insert), u.fmt_seconds(elapsed), len(insert)/elapsed,
#              (j+1)*inner_ct, (j+1)*inner_ct/(outer_ct*inner_ct)))

# os.system('clear-disk-cache')

# db.execute('SELECT * FROM ts')
# while True:
#    start = time.time()
#    results = db.fetchmany(inner_ct)
#    if (len(results) == 0):
#       break
#    end = time.time()
#    elapsed = end - start
#    l.info('fetched %d vectors in %s (%d/s), %d, %.3f'
#           % (len(results), u.fmt_seconds(elapsed), len(results)/elapsed,
#              (j+1)*inner_ct, (j+1)*inner_ct/(outer_ct*inner_ct)))

#end_out = time.time()
#elapsed_out = end_out - start_out
#l.info('%d vectors in %s (%d/s)'
#       % (outer_ct * inner_ct, u.fmt_seconds(elapsed_out),
#          (outer_ct * inner_ct)/elapsed_out))
#u.memory_use_log()

l.info('closing database')
db.close()
#u.memory_use_log()
