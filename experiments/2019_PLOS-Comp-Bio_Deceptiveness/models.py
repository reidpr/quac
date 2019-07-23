import abc
import metrics
import pandas as pd
import sklearn.linear_model
import sklearn.model_selection
import u

import numpy as np


def linear_fit(features, incidence, penalty, lambda_):
   """Fit features (X) to incidence (y) and return the coefficients. The number
      of coefficients will be one more than the number of features, because
      the last one is the intercept."""
   # Add a non-penalized column for the intercept.
   features = features.copy()
   features.loc[:,len(features.columns)] = 1
   diagonal = np.diagflat(np.append(penalty, 0))
   # FIXME: Dave: Do we want the pseudoinverse? Why or why not?
   # Note: dot() is matrix multiply here.
   xx = features.T.dot(features)
   xy = features.T.dot(incidence)
   inv = xx + lambda_ * diagonal
   return pd.Series(np.linalg.inv(inv).dot(xy), index=features.columns)

def linear_predict(features, beta, index):
   features = features.copy()
   features.loc[:,len(features.columns)] = 1
   return pd.Series(features.dot(beta), index=index)

def normalize(fs):
   # Return normalized copy of features dataframe fs (i.e., mean zero and
   # standard deviation 1).
   return (fs - fs.mean(axis=0)) / fs.std(axis=0)

def normalized_p(fs, epsilon=1e-6):
   # Return True if dataframe fs contains normalized features, False
   # otherwise.
   return (    (fs.mean(axis=0).abs() <= epsilon).all()
           and ((fs.std(axis=0) - 1).abs() <= epsilon).all())


class Decoder(abc.ABC):

   # A Decoder instance embodies a specific experimental condition. The
   # factor values are expressed as follows:
   #
   #   1. Class of features:    attribute features_name
   #   2. Training period:      attribute training_start
   #   3. Deceptiveness noise:  attribute decept_noise
   #   4. Model type:           subclass name
   #
   # These factors are included for reference but are not used in training or
   # prediction.
   #
   # Additional attributes:
   #
   #   incidence        series: index: weeks
   #   features         dataframe: cols: feature id, rows: weeks
   #   decept           series: index: feature id
   #   prediction       series: index: weeks
   #   lambda_cv        series: index: (lambda, fold index)
   #   lambda_cv_means  series: index: lambda

   __slots__ = ("features_name",   # str
                "training_start",  # int
                "decept_noise",    # float
                "incidence",       # series
                "features",        # dataframe
                "decept",          # series
                "prediction",      # series
                "lambda_cv",       # series
                "lambda_cv_means") # series


   def __init__(self, incidence,
                features, features_name,
                decept, decept_noise,
                training_start):
      [setattr(self, k, v) for (k, v) in locals().items() if k != 'self']

      assert incidence.index[0] == pd.Timestamp(u.start)
      assert features.index.equals(incidence.index)
      assert decept.index.equals(features.columns)
      assert 0 <= decept_noise <= 1
      assert 0 <= training_start <= 2
      assert decept.index.equals(features.columns)
      assert normalized_p(features)

      self.prediction = pd.Series(index=self.incidence.index)
      self.prediction.name = str(self)

      self.lambda_cv = None
      self.lambda_cv_means = None

   def __repr__(self):
      return f"""\
{self.name}:
  reference data:  {self.incidence.name} ({len(self.incidence)} weeks)
  features:        {self.features_name} ({len(self.features.columns)} of them)
  decept. noise:   {self.decept_noise}
  training start:  {self.training_start}"""

   def __str__(self):
      return (  "%s / %s / %0.2f %d"
              % (self.name, self.features_name,
                 self.decept_noise, self.training_start))

   @property
   def features_test(self):
      return self.features.loc[u.test_start:u.test_end]

   @property
   def features_train(self):
      return self.features.loc[u.seasons[self.training_start][0]:u.train_end]

   @property
   def incidence_test(self):
      return self.incidence.loc[u.test_start:u.test_end]

   @property
   def incidence_train(self):
      return self.incidence.loc[u.seasons[self.training_start][0]:u.train_end]

   @property
   def prediction_test(self):
      return self.prediction.loc[u.train_start:u.train_end]

   @property
   def prediction_train(self):
      return self.prediction.loc[u.test_start:u.test_end]

   def evaluate(self, season_i, metric_f):
      assert (season_i in (3, 4))
      (start, end) = u.seasons[season_i]
      return metric_f(self.prediction, self.incidence.loc[start:end])

   def lambdas_cross_validate(self, lambdas, fold_ct):
      pass  # default implementation: no-op

   def predict(self):
      self.predict_real()
      assert self.prediction.isnull().sum() == 0, "NaNs predicted: %s" % self

   @abc.abstractmethod
   def predict_real(self):
      ...

   @abc.abstractmethod
   def train(self, lambda_):
      ...


class Straw_Man_Conservative(Decoder):

   # For week i, predict the indicence reference value at week i-1.
   name = "SMC"

   def predict_real(self):
      # Week 0 prediction has no previous week, so just use the week 0 value.
      self.prediction.iloc[0] = self.incidence.iloc[0]
      for i in range(1, len(self.prediction.index)):
         self.prediction.iloc[i] = self.incidence.iloc[i-1]

   def train(self, lambda_):
      # Because this model cheats, we don't need to train.
      pass


class Straw_Man_Mean(Decoder):

   # Predict the mean of the training period.
   name = "SMM"

   def predict_real(self):
      self.prediction[:] = self.mean

   def train(self, lambda_):
      self.mean = self.incidence_train.mean()


# Use sklearn's ridge regression
# Sanity check to verify that our implemented ridge produces the same output
class Straw_Man_Ridge(Decoder):

   name = 'SMR'

   def predict_real(self):
      self.prediction = pd.Series(self.classifier.predict(self.features),
                                  index=self.prediction.index)

   def train(self, lambda_):
      # alpha: regularization strength
      # fit_intercept: fit an intercept or not?
      # normalize: normalize? Probably false, b/c we will do ourselves
      # solver: alg to solve, think we want cholesky?? DAVE/ REID
      # tol: precision of the solution
      clf = sklearn.linear_model.Ridge(alpha=lambda_, solver="cholesky",
                                       fit_intercept=True)
      clf.fit(self.features_train, self.incidence_train)
      self.beta = pd.Series(clf.coef_, index=self.features.columns)
      self.classifier = clf


class Fridge(Decoder):

   # Additional attributes:
   #
   #   beta         series: estimated feature weights; index: feature names

   __slots__ = ("beta")

   @property
   @abc.abstractmethod
   def penalty(self):
      ...

   def lambdas_cross_validate(self, lambdas, fold_ct):
      # Use cross-validation to test the lambdas. Set self.lambda_cv to a
      # series with index (lambda, fold index) and one column RMSE.
      index = pd.MultiIndex.from_product([lambdas, range(fold_ct)],
                                         names=["lambda", "fold"])
      out = pd.Series(index=index, name="RMSE", dtype=np.float64)
      for lambda_ in lambdas:
         folds =  sklearn.model_selection.KFold(fold_ct, shuffle=False) \
                 .split(self.features_train, self.incidence_train)
         for (fold_idx, (cv_train_is, cv_test_is)) in enumerate(folds):
            X_train = self.features_train.iloc[cv_train_is]
            y_train = self.incidence_train.iloc[cv_train_is]
            X_test = self.features_train.iloc[cv_test_is]
            y_test = self.incidence_train.iloc[cv_test_is]
            betas = linear_fit(X_train, y_train, self.penalty, lambda_)
            y_predicted = linear_predict(X_test, betas, y_test.index)
            out.loc[lambda_,fold_idx] = metrics.rmse(y_test, y_predicted)
      self.lambda_cv = out
      self.lambda_cv_means = out.groupby(["lambda"]).mean()  # avg across folds

   def predict_real(self):
      self.prediction = linear_predict(self.features, self.beta,
                                       self.prediction.index)

   def train(self, lambda_):
      self.beta = linear_fit(self.features_train, self.incidence_train,
                             self.penalty, lambda_)

   ### FIXME

   def lambda_eval(self, y_predicted, y_goldstandard):
      ## something that compares prediction to the actual values
      ## arbitrarily selected r2
      return m.r2(y_predicted, y_goldstandard)

   def ridge_predict(self,X_test, y_test, betas):
      X_test[len(X_test.columns)] = 1 # for intercept
      return pd.Series(X_test.dot(betas), index=y_test.index)


class Ridge(Fridge):

   name = "ridge"

   @property
   def penalty(self):
      return np.ones(len(self.features.columns))


class Fridge_Threshold(Fridge):

   name = "threshold fridge"
   threshold = 0.35

   @property
   def penalty(self):
      p = pd.Series(index=self.decept.index)
      p.loc[:] = 1                                # assume everyone is a loser
      p.loc[self.decept <= self.threshold] = 0.1  # winners: low deceptiveness
      return p


class Fridge_Exponential(Fridge):

   __slots__ = ('exponent')

   def __init__(self, exponent=None, **kwargs):
      assert exponent is not None
      self.exponent = exponent
      super().__init__(**kwargs)

   @property
   def name(self):
      return "exponent %g fridge" % self.exponent

   @property
   def penalty(self):
      return self.decept ** self.exponent


class Fridge_Linear(Fridge):

   name = "linear fridge"

   @property
   def penalty(self):
      return self.decept


class Fridge_Quadratic(Fridge_Exponential):

   name = "quadratic fridge"

   def __init__(self, **kwargs):
      kwargs["exponent"] = 2
      super().__init__(**kwargs)


class Fridge_Quartic(Fridge_Exponential):

   name = "quartic fridge"

   def __init__(self, **kwargs):
      kwargs["exponent"] = 4
      super().__init__(**kwargs)
