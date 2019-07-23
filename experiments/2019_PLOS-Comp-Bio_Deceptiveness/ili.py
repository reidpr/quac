import pandas as pd

import u

# data sets
us_full = None
us_national = None
us_national_train = None
us_national_test = None

def load():

   global us_full
   us_full = pd.read_excel(u.datapath / 'S1_Dataset_ILI.xls', index_col=0)

   global us_national
   us_national = us_full["national"].loc[u.start:u.end]
   us_national.name = "U.S. ILI"
   assert (len(us_national) == 261)

   global us_national_train
   us_national_train = us_full["national"].loc[u.train_start:u.train_end]
   us_national_train.name = "U.S. ILI (training)"

   global us_national_test
   us_national_test = us_full["national"].loc[u.test_start:u.test_end]
   us_national_test.name = "U.S. ILI (testing)"
