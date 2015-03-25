import gc
import h5py
import memory_profiler
import numpy as np
import sys
import time

ds_len = int(sys.argv[2])
ds_count = int(sys.argv[3])
close_interval = int(sys.argv[4])

#gc.set_debug(gc.DEBUG_LEAK | gc.DEBUG_STATS)

def test(prefix, item_ct, loop_ct):
   h5 = h5py.File(sys.argv[1], 'a')
   cc = h5.id.get_mdc_config()
   print(cc.max_size)
   print(h5.id.get_access_plist().get_cache())
   cc.min_size = 1024*1024
   cc.max_size = 1024*1024
   h5.id.set_mdc_config(cc)
   #h5.create_group(b'\xff')  # force new compact-or-indexed group with high byte
   #del h5[b'\xff']
   print('start  %s %.3f' % (prefix, time.time() - start))
   path_i = 0
   for i in range(loop_ct):
      data = np.zeros(item_ct, dtype=np.float32)
      i_str = '%05d' % i
      #path = ''
      #path = '/'.join((prefix, i_str[0], i_str[1], i_str[2], i_str[3]))
      path = str(path_i)
      #print(path + '/' + str(i))
      ds = h5.create_dataset(path + '/' + str(i), data=data)
      #ds = h5.create_dataset(path + '/' + str(i), (item_ct,), dtype=np.float32)
      #ds[:] = data
      #h5.create_group(path + '/' + i_str)
      if (i != 0 and i % close_interval == 0):
         path_i += 1
         #print(i, '%.1f' % (time.time() - start), h5.id.get_mdc_size(), h5.id.get_mdc_hit_rate())
         print(i, '%.1f' % (time.time() - start), h5.id.get_mdc_size(), h5.id.get_mdc_hit_rate(), memory_profiler.memory_usage(-1))
   print('end    %s %.3f' % (prefix, time.time() - start))
   h5.close()

start = time.time()
test('a', ds_len, ds_count)
#gc.collect()
#time.sleep(3)
#test('b', ds_len, ds_count)
