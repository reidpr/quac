'''
Compare classification run-time versus number of tweets.
'''
import math
import time

import numpy as np
from scipy.sparse import coo_matrix, vstack
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from termcolor import colored

import testable
import tweet
import u

l = u.l
rand = np.random.mtrand.RandomState(12345)


### Setup ###

ap = u.ArgumentParser(description=__doc__)
gr = ap.add_argument_group('arguments')
gr.add_argument("--slices",
                metavar='SLICES',
                default='100000:1000001:100000',
                help="slices of sizes for timing curve. ",
                )
gr.add_argument("--test-size",
                metavar='N',
                type=int,
                default=1000000,
                help="number of tweets to classify. duplicates used as needed. ",
                )
gr.add_argument("--train-size",
                metavar='N',
                type=int,
                default=10000,
                help="number of tweets to train on. ",
                )
gr.add_argument('tsv_files',
                metavar='TSV',
                nargs='+',
                help='.tsv files to add to metadata')


def resize(tweets, size):
   '''Add duplicates or remove tweets until reach specified size.
   tweets .... sparse matrix of word counts
   size   .... desired number of tweets
   >>> resize(coo_matrix([1, 2, 3]), 5).shape[0]
   5
   >>> resize(coo_matrix([1, 2, 3]), 9).shape[0]
   9
   >>> resize(coo_matrix([1, 2, 3]), 2).shape[0]
   2
   >>> resize(coo_matrix([1, 2, 3]), 3).shape[0]
   3
   '''
   while tweets.shape[0] < size:
      tweets = vstack([tweets, tweets])
   return tweets.tocsr()[:size]


def time_it(clf, tweets):
   t_start = time.time()
   clf.predict(tweets)
   return time.time() - t_start


def main():
   tweets = read_tsvs(args.tsv_files)
   tweets = CountVectorizer(min_df=0.).fit_transform(tweets)
   l.info('read tweets with dimension %s', tweets.shape)
   tweets = resize(tweets, args.test_size)
   l.info('resized to %s', tweets.shape)
   l.info('training on %d random instances.' % args.train_size)
   classifiers = [
      LogisticRegression(),
      MultinomialNB(),
#      SVC(kernel='linear'),  # too slow! (orders of magnitude)
      ]
   y = rand.random_integers(0, 1, args.train_size)
   for c in classifiers:
      c.fit(tweets[:args.train_size], y)
   l.info('beginning testing. all times in seconds.')
   slices = [int(x) for x in args.slices.split(':')]
   sizes = range(args.test_size + 1)[slices[0]:slices[1]:slices[2]]
   l.info('    model name   \t' + '\t'.join(str(s) for s in sizes))
   times = []
   for clf in classifiers:
      clf_times = []
      for size in sizes:
         clf_times.append('%.5f' % time_it(clf, tweets[:size]))
      l.info(clf.__module__[-15:] + '\t' + '\t'.join(clf_times))


def read_tsvs(filenames):
   tweets = []
   ct = 0
   for filename in filenames:
      reader = tweet.Reader(filename)
      for tw in reader:
          tweets.append(tw.text)
          ct += 1
          if ct > args.test_size:
              return tweets
   return tweets


### Bootstrap ###

try:
   args = u.parse_args(ap)
   u.logging_init('clsbmk')

   if (__name__ == '__main__'):
      main()

except testable.Unittests_Only_Exception:
   testable.register('')
