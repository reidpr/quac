#!/usr/bin/env python

import pickle
import sys
import time
import types

import joblib as jl
import numpy as np
import pandas as pd
import scipy.stats

import google_health_trends as ght
import ili
import wikipedia as wp
import metrics
import models
import noise
import u

if (__name__ == "__main__"):
   print("initializing")


# When did we start?
t_start = time.time()

# Load data.
ili.load()
wp.load()
ght.load()

# Set up synthetic features, but don't draw any yet because the random seed
# isn't initialized.
idx = ili.us_national.index
systematic_bases = pd.concat([
   noise.pulse(idx, [("2012-02-05", 8),
                     ("2013-02-03", 8),
                     ("2014-02-02", 8),
                     ("2015-02-01", 8),
                     ("2016-02-07", 8)], name="oprah annual"),
   noise.pulse(idx, [("2013-02-03", 8),
                     ("2015-02-01", 8),
                     ("2016-02-07", 8)], name="oprah fore"),
   noise.pulse(idx, [("2015-02-01", 8),
                     ("2016-02-07", 8)], name="oprah late"),
   noise.linear(idx, name="drift steady"),
   noise.linear(idx, "2014-07-06", "2015-07-12", name="drift late"),
   noise.sin(idx, 5, phase=0.75, name="cycle annual"),
   noise.sin(idx, 5, phase=0.75, end="2014-12-28", name="cycle ending"),
], axis=1)
syn_maker = noise.Feature_Maker_Dirichlet(ili.us_national, systematic_bases)

# factors
f_feature_name = ["synthetic", "raw", "topic"]
f_training_start = [0, 1, 2]
f_decept_noise = [0.00, 0.05, 0.15, 0.40, 1.00]
f_model_class = [#models.Straw_Man_Mean,
                 #models.Straw_Man_Conservative,
                 models.Ridge,
                 #models.Straw_Man_Ridge,
                 models.Fridge_Threshold,
                 models.Fridge_Linear,
                 models.Fridge_Quadratic,
                 models.Fridge_Quartic]
f_condition_ct = (  len(f_feature_name) * len(f_training_start)
                  * len(f_decept_noise) * len(f_model_class))
# synthetic feature parameters
sf_feature_ct = 500
sf_alpha_srs = [1.0, 0.5, 1.5]
sf_alpha_odc = [0.3, 0.3, 0.3]
# evaluation metrics
e_seasons = [3, 4]
e_functions = [metrics.hit_rate,
               metrics.peak_intensity_abs,
               metrics.peak_timing_abs,
               metrics.r2,
               metrics.rmse]
# regularization weight
lambda_ = None
lambda_cv_min = -1
lambda_cv_max =  7
lambda_cv_step_ct = (lambda_cv_max - lambda_cv_min) * 5 + 1
lambda_cv_fold_ct = 10


def main():

   INFO("starting")
   np.random.seed(u.random_seed)
   out = dict()
   out["features"] = dict()
   out["decept"] = dict()
   out["models"] = dict()
   out["results"] = dict()
   out["synthetic_draws"] = None

   INFO("drawing %d random features" % sf_feature_ct)
   (features_syn, decept_syn, draws) = \
      syn_maker.features_draw(sf_feature_ct, alpha_srs=sf_alpha_srs,
                              alpha_odc=sf_alpha_odc)
   features_syn = models.normalize(features_syn)
   assert sf_feature_ct == len(features_syn.columns)
   out["features"]["synthetic"] = features_syn
   out["synthetic_draws"] = draws
   out["decept"].setdefault("synthetic", dict())[0.0] = decept_syn

   INFO("setting up GHT features")
   out["features"]["raw"] = models.normalize(ght.raws)
   out["decept"].setdefault("raw", dict())[0.0] \
      = ght.raw_decept.loc[:,"decept"]
   out["features"]["topic"] = models.normalize(ght.topics)
   out["decept"].setdefault("topic", dict())[0.0] \
      = ght.topic_decept.loc[:,"decept"]

   INFO("drawing noisy deceptiveness")
   for fn in f_feature_name:
      for dn in f_decept_noise[1:]:
         out["decept"][fn][dn] = noise.decept_draw(dn, out["decept"][fn][0])

   INFO("building dictionary of %d models" % f_condition_ct)
   condition_ct = 0
   for fn in f_feature_name:
      for ts in f_training_start:
         for dn in f_decept_noise:
            for mc in f_model_class:
               condition_ct += 1
               out["models"].setdefault(fn, dict()) \
                            .setdefault(ts, dict()) \
                            .setdefault(dn, dict()) \
                            [mc.name] = mc(features_name=fn,
                                           training_start=ts,
                                           decept_noise=dn,
                                           incidence=ili.us_national,
                                           features=out["features"][fn],
                                           decept=out["decept"][fn][dn])
   assert condition_ct == f_condition_ct

   global lambda_
   if (lambda_ is not None):
      INFO("lambda provided, skipping cross-validation")
      out["lambda_cv_means_bests"] = None
      out["lambda_cv_means_bias"] = None
      out["lambda_cv_selected"] = None
   else:
      INFO("cross validating lambda: 10^%d to 10^%d, %d steps, %d folds"
           % (lambda_cv_min, lambda_cv_max, lambda_cv_step_ct,
              lambda_cv_fold_ct))
      lambdas = np.logspace(lambda_cv_min, lambda_cv_max, lambda_cv_step_ct)
      means_bias = None
      best = list()
      for m in u.dict_nested_values(out["models"]):
         m.lambdas_cross_validate(lambdas, lambda_cv_fold_ct)
         if (m.lambda_cv is not None):
            # bias the minimum toward the middle
            if (means_bias is None):
               means_bias = m.lambda_cv_means.copy()
               means_bias.loc[:] = np.linspace(-1.0, 1.0, len(means_bias))
               means_bias.loc[:] **= 2
               means_bias.loc[:] *= 0.02
               out["lambda_cv_means_bias"] = means_bias
            # compute the best lambda for this model
            means_biased = m.lambda_cv_means + means_bias
            rmse = means_biased.min()
            lambda_best = means_biased.idxmin()
            INFO("%s: lambda = %g, RMSE = %g" % (m, lambda_best, rmse))
            best.append(lambda_best)
      out["lambda_cv_means_bests"] = best
      lambda_ = scipy.stats.gmean(best)
      out["lambda_cv_selected"] = lambda_

   INFO("training with lambda = %g" % lambda_)
   for m in u.dict_nested_values(out["models"]):
      m.train(lambda_)

   INFO("predicting")
   for m in u.dict_nested_values(out["models"]):
      m.predict()

   INFO("evaluating")
   for ef in e_functions:
      cols = pd.MultiIndex.from_product([f_feature_name,
                                         (mc.name for mc in f_model_class)],
                                        names=["features", "model"])
      rows = pd.MultiIndex.from_product([f_decept_noise,
                                         e_seasons,
                                         f_training_start],
                                         names=["decept noise",
                                                "test season",
                                                "training start"])
      df = pd.DataFrame(columns=cols, index=rows, dtype="float64")
      for s in e_seasons:
         for m in u.dict_nested_values(out["models"]):
               df[m.features_name,m.name] \
                 [m.decept_noise,s,m.training_start] \
                   = m.evaluate(s, ef)
      out["results"][ef.__name__] = df

   INFO("writing output file")
   with open(u.datapath_tl / "out.pickle", "wb") as fp:
      pickle.dump(out, fp, protocol=pickle.HIGHEST_PROTOCOL)

   INFO("done")


def INFO(*args, **kwargs):
   print("%6.2f" % (time.time() - t_start), end=" ")
   print(*args, **kwargs)


if (__name__ == "__main__"):
   if (len(sys.argv) >= 2):
      lambda_ = float(sys.argv[1])
   main()
