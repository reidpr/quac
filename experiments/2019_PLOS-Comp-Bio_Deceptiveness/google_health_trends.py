import pandas as pd

import u
import wikipedia as wp

# data sets
raws = None
topics = None

# deceptiveness
raw_decept = None
topic_decept = None


def deceptiveness(distance):
   assert 1 <= distance <= 7
   return 0.90 * (distance-1)/6 + 0.05  # evenly spaced between 0.05 and 0.95

def load():

   def decept_df(features, distances):
      distances = pd.DataFrame.from_dict(distances, orient="index",
                                         dtype="float64")
      decept = pd.DataFrame(index=features.columns,
                            columns=["distance", "decept"], dtype="float64")
      decept.loc[:,"distance"] = distances.loc[:,0]
      assert features.columns.equals(decept.index)
      decept.loc[:,"decept"] \
         = decept.apply(lambda row: deceptiveness(row["distance"]), axis=1)
      return decept

   # Load full data dump. Ignore category distances since we have that as
   # dictionaries in wikipedia.py.
   df = pd.read_csv(u.datapath_tl / "en+Influenza.ght.csv",
                    header=0, skiprows=[1,], index_col=0, parse_dates=[0])
   df.sort_index(axis=1, inplace=True)

   # Remove columns that don't have enough data.
   df = df.loc[:, (df == 0).sum()/len(df.index) <= u.ght_zero_threshold]

   # Rescale everything so the unit is fraction of queries, not queries per
   # ten million.
   df /= 1e7

   # Raw queries end in non-close paren.
   global raws, raw_decept
   raws = df.filter(regex=r"[^)]$")
   raw_decept = decept_df(raws, wp.ght_raw_distances)

   # Topics end in close paren.
   global topics, topic_decept
   topics = df.filter(regex=r"\)$")
   topic_decept = decept_df(topics, wp.ght_topic_distances)

