import tinysegmenter

from . import base
import testable


class Tzer(base.Tzer):
   '''A wrapper for the TinySegmenter tokenizer for Japanese. e.g.:

      >>> Tzer(1).tokenize(base.T_JP) == base.T_JP_TOKS
      True'''

   def __init__(self, ngram):
      base.Tzer.__init__(self, ngram)
      self.seg = tinysegmenter.TinySegmenter()

   def tokenize_real(self, text):
      return [i.lower() for i in self.seg.tokenize(text)]


testable.register('')
