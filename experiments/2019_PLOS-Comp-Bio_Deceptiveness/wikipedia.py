# Note: In our experiment, the category distance between Wikipedia articles
# was loaded from a Python pickle file. The same information is available in
# S2, so this version of the code loads it from there instead. We have verifed
# that the two are identical.

import gzip
import pickle
import re
import urllib

import pandas as pd
import unidecode

import u


# data sets
wiki_distances = None
ght_raw_distances = None
ght_topic_distances = None

# maps
raw2wiki = None
top2wiki = None

def load():
   #load_wiki_distances()
   load_ght_distances()

def load_ght_distances():

   # note that empty cells yield the empty string, not None or NaN
   df = pd.read_excel(u.datapath / "S2_Dataset_en+Influenza.xlsx", use_cols=4,
                      index_col=0, skiprows=1, na_filter=False)
   assert (df.duplicated("raw query").any() == False)
   assert ( df.loc[df["topic"] != "",:]
            .duplicated("topic").any() == False)
   assert (all([i[-1] == ")" for i in df.loc[df["topic"] != "","topic"]]))
   assert ( df.loc[df["topic code"] != "",:]
            .duplicated("topic code").any() == False)

   global raw2wiki
   raw2wiki = { q:a for a,q in df.loc[:,"raw query"].to_dict().items() }
   assert (len(raw2wiki) == len(df))
   global top2wiki
   top2wiki = { t:a for a,t in df.loc[:,"topic"].to_dict().items() if t != "" }
   assert (len(top2wiki) <= len(df))

   # Original experiment code to compute Wikipedia distance map.
   #ght_raw_distances_X = { q:wiki_distances[a] for q,a in raw2wiki.items() }
   #ght_topic_distances_X = { q:wiki_distances[a] for q,a in top2wiki.items() }

   # New, equivalent code.
   global ght_raw_distances
   ght_raw_distances = { r["raw query"]:r["distance"]
                         for (i, r) in df.iterrows() }
   global ght_topic_distances
   ght_topic_distances = { r["topic"]:r["distance"]
                           for (i, r) in df.iterrows()
                           if r["topic"] is not "" }

   # Verify the two are the same.
   #assert (ght_raw_distances == ght_raw_distances_X)
   #assert (ght_topic_distances == ght_topic_distances_X)

def load_wiki_distances():
   gr = pickle.load(gzip.open(u.datapath / "wiki-graph.pkl.gz"))
   global wiki_distances
   wiki_distances = { k[3:]:v for k,v in gr["en+Influenza"].items() }

def write_raw_queries():

   def to_query(x):
      x = urllib.parse.unquote(x)          # urldecode
      x = x.replace("_", " ")              # underscore to space
      x = re.sub(r" \(.+\)", "", x)        # remove parenthetical
      x = unidecode.unidecode(x)           # remove accents
      x = x.lower()                        # to lower-case
      x = re.sub(r"[^a-z0-9/' -]", "", x)  # simplify character set
      # remove phrases no person would type into a search box
      for i in [r" and\b",
                r"^global ",
                r"^influenza .? virus subtype ",
                r"^list of ",
                r"^the "]:
         x = re.sub(i, "", x)
      return x

   rows = { k: (v, to_query(k)) for (k, v) in wiki_distances.items() }
   wp = pd.DataFrame.from_dict(rows, orient="index")
   wp.columns = ["distance", "raw query"]
   wp.index.name = "article"

   # There's one duplicate query, from "Hemagglutinin" and
   # "Hemagglutinin (influenza)". Prefer the latter.
   wp.drop("Hemagglutinin", inplace=True)
   assert (len(wp["raw query"]) == len(set(wp["raw query"])))

   wp.to_csv(str(u.datapath / "raw/en+Influenza.csv"))
