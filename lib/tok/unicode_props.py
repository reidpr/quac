# Copyright (c) Los Alamos National Security, LLC, and others.

import itertools
import operator

import unicodedata2

from . import base
from . import tiny
import testable


class UP_Tiny(base.Tzer):
   '''Tokenize based on Unicode properties (see [1] and [2]) and invoke Tiny
      as needed. The basic algorithm is:

        1. Split into candidate tokens: sequences of characters with the same
           character category and script.

        2. Candidates which are not of the "letter" category are discarded.

        3. Candidates in the following scripts are discarded because they:

           ... do not separate words with a delimeter [3]:

             Thai (Thai)
             Lao (Lao)
             Khmer (Cambodian)
             Myanmar (Burmese)

           ... may not really be letters:

             Common
             Inherited

        4. Candidates in the following scripts are assumed to be Japanese and
           passed on to Tiny for further decomposition (Chinese has low use on
           Twitter, so we ignore that problem):

             Han (Kanji)
             Hiragana
             Katakana

      FIXME: This doesn't do anything special with apostrophes; e.g.,
      "doesn't" will be come two tokens "doesn" and "t". There may be other
      Unicode characters with similar joining properties.

      FIXME: We may be just reimplementing ICU, but badly.

      [1]: http://en.wikipedia.org/wiki/Unicode_character_property#General_Category
      [2]: http://en.wikipedia.org/wiki/Scripts_in_Unicode
      [3]: http://stackoverflow.com/questions/1605353 (unreliable?)'''

   DISCARD_SCRIPTS = set(('Thai', 'Lao', 'Khmer', 'Myanmar',
                          'Common', 'Inherited'))
   JP_SCRIPTS = set(('Han', 'Hiragana', 'Katakana'))

   def __init__(self, ngram):
      base.Tzer.__init__(self, ngram)
      self.tiny = tiny.Tzer(ngram)

   def tokenize_real(self, text):
      chars = ((unicodedata2.script_cat(c), c) for c in text)
      tokens = list()
      for (key, group) in itertools.groupby(chars, operator.itemgetter(0)):
         if (key[1][0] == 'L' and key[0] not in self.DISCARD_SCRIPTS):
            cand = ''.join((c[1] for c in group))
            if (key[0] in self.JP_SCRIPTS):
               tokens.extend(self.tiny.tokenize(cand))
            else:
               tokens.append(cand.lower())
      return tokens


testable.register('''

>>> all([s in unicodedata2.script_data['names']
...      for s in UP_Tiny.DISCARD_SCRIPTS])
True
>>> all([s in unicodedata2.script_data['names']
...      for s in UP_Tiny.JP_SCRIPTS])
True
>>> UP_Tiny(1).tokenize(base.T_EN) == base.T_EN_TOKS
True
>>> UP_Tiny(1).tokenize(base.T_FR) == base.T_FR_TOKS
True
>>> UP_Tiny(1).tokenize(base.T_JP) == base.T_JP_TOKS
True
>>> (UP_Tiny(1).tokenize(base.T_JP + ' ' + base.T_FR)
...  == base.T_JP_TOKS + base.T_FR_TOKS)
True
>>> UP_Tiny(1).tokenize(base.T_PUNCT) == base.T_PUNCT_TOKS
True
>>> UP_Tiny(1).tokenize(base.T_WEIRD) == base.T_WEIRD_TOKS
True

''')
