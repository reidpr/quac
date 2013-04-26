# -*- coding: utf-8 -*-

import re

import icu  # testable.SKIP_IF_NOT_FOUND

from . import base
from . import tiny
import multicore
import testable


def is_japanese(text):
   u'''Return true if text appears to contain Japanese.

       >>> is_japanese(base.T_JP2)
       True
       >>> is_japanese(base.T_EN)
       False
       >>> is_japanese(base.T_KO)
       False
       >>> is_japanese(base.T_CH)  # FIXME: really should be False
       True'''
   # See http://stackoverflow.com/a/2857434
   # FIXME: The Kanji range (4E00-9FBF) may also catch Chinese.
   return (re.search(u'[\u4E00-\u9FBF\u3040-\u309F\u30A0-\u30FF]', text)
           is not None)

def is_latin(text):
   # FIXME: This function is likely overly restrictive, because there are
   # many "Latin" characters which can't be put in ISO 8859-1.
   u'''
   >>> is_latin(u'Hello')
   True
   >>> is_latin(u'àçúÈÑ')
   True
   >>> is_latin(u'ص')
   False
   >>> is_latin(u'щф')
   False
   >>> is_latin(u'βπ')
   False
   '''
   try:
      text.encode('iso8859_1')
   except:
      return False
   else:
      return True


class ICU(base.Tzer):
   u'''A wrapper for the PyICU tokenizer, which is based on the International
      Components for Unicode (ICU):
      http://lucene.apache.org/core/old_versioned_docs/versions/3_1_0/api/contrib-icu/index.html

      ngrams ........... number of ngrams. E.g., if 2, (dog jumped) -> [dog,
                         jumped, dog jumped]

      must_have_alnum .. every token must have some alpha numeric character
                         (e.g., not just be punctuation)

      This is a very simple tokenizer -- each punctuation mark is a separate
      token. For Chinese, each character is a separate token.

      Locale allegedly makes no difference except for Thai:
      http://two.pairlist.net/pipermail/reportlab-users/2010-July/009618.html
      Confirmed by a few examples.

      Note on apostrophes:
      "Apostrophes or hyphens within a word are kept with the word. They are
      not broken out separately like most other punctuation"
      http://userguide.icu-project.org/boundaryanalysis

      >>> ICU(1).tokenize(base.T_EN) == base.T_EN_TOKS_ICU
      True
      >>> ICU(1, must_have_alnum=False).tokenize(base.T_EN) == base.T_EN_TOKS_PUNC_ICU
      True
      >>> ICU(1).tokenize(base.T_PUNCT) == base.T_PUNCT_TOKS
      True
      >>> ICU(1).tokenize(base.T_FR) == base.T_FR_TOKS
      True
      '''

   def __init__(self, ngram, locale=icu.Locale.getDefault(),
                must_have_alnum=True):
      #assert (multicore.core_ct == 1)  # ICU hangs under multicore
      base.Tzer.__init__(self, ngram)
      self.locale = locale
      self.iterator = icu.BreakIterator.createWordInstance(self.locale)
      self.must_have_alnum = must_have_alnum

   def is_word(self, s):
      '''A word is: (a) not empty, (b) not a space, (c) if must_have_alnum is
         True, contains at least one alpha-numeric.
      >>> t = ICU(1,must_have_alnum=True)
      >>> t.is_word('hello') and t.is_word("didn't")
      True
      >>> t.is_word(' ') or t.is_word(None) or t.is_word("!@#$%^&*'")
      False
      >>> t.must_have_alnum=False
      >>> t.is_word('hello') and t.is_word("didn't") and t.is_word("!@#$%^&*'")
      True
      >>> t.is_word(' ')
      False
      '''
      return s and not s.isspace() and \
          (not self.must_have_alnum or any(ch.isalnum() for ch in s))

   def tokenize_real(self, text):
      tokens = []
      pos = 0
      self.iterator.setText(text)
      for nextpos in self.iterator:
         token = text[pos:nextpos].strip()
         if (self.is_word(token)):
           tokens.append(token.lower())
         pos = nextpos
      return tokens


class Tiny_ICU(base.Tzer):
   u'''Splits on whitespace, then uses ICU for Latin, Tiny for Japanese.
       Ignores everything else. E.g.:

       >>> Tiny_ICU(1).tokenize(base.T_JP + ' ' + base.T_FR) == base.T_JP_TOKS + base.T_FR_TOKS
       True
       >>> Tiny_ICU(1).tokenize(base.T_PUNCT) == base.T_PUNCT_TOKS
       True'''

   def __init__(self, ngram):
      base.Tzer.__init__(self, ngram)
      self.tiny = tiny.Tzer(ngram)
      self.icu = ICU(ngram)

   def tokenize_real(self, text):
      ws_tokens = text.split()
      tokens = []
      for ws_token in ws_tokens:
         if (is_latin(ws_token)):
            tokens.extend(self.icu.tokenize(ws_token))
         elif (is_japanese(ws_token)):
            tokens.extend(self.tiny.tokenize(ws_token))
      return tokens


testable.register(u'''

>>> Tiny_ICU(1).tokenize(base.T_PUNCT) == base.T_PUNCT_TOKS
True

''')
