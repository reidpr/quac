# Copyright © Los Alamos National Security, LLC, and others.

from pprint import pprint
import time

from bsddb3 import db as bdb
import numpy as np

import u

outer_ct = 5
inner_ct = 50000

u.logging_init('bdb', verbose_=True)
l = u.l

u.memory_use_log()

db = bdb.DB()
#db.set_flags(bdb.DB_TXN_NOT_DURABLE)
db.set_cachesize(0, 32*1024*1024)
db.set_pagesize(64*1024)
db.open('/data6/foo.db', dbtype=bdb.DB_BTREE, flags=(bdb.DB_CREATE))

start_out = time.time()
for j in range(outer_ct):
   start = time.time()
   for i in range(inner_ct):
      db.put(str(j * inner_ct + i).encode('UTF-8'),
             np.ones(720, dtype=np.int32))
   db.sync()
   end = time.time()
   elapsed = end - start
   l.info('%d vectors in %s (%d/s), %.3f'
          % (inner_ct, u.fmt_seconds(elapsed), inner_ct/elapsed,
             (j+1)*inner_ct/(outer_ct*inner_ct)))
   u.memory_use_log()

l.info('compacting database')
pprint(db.stat())
db.compact(flags=bdb.DB_FREE_SPACE)
l.info('closing database')
pprint(db.stat())
db.close()
end_out = time.time()
elapsed_out = end_out - start_out
l.info('%d vectors in %s (%d/s)'
       % (outer_ct * inner_ct, u.fmt_seconds(elapsed_out),
          (outer_ct * inner_ct)/elapsed_out))
u.memory_use_log()
