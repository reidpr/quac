# -*- coding: utf-8 -*-

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

# A note on implementation of ngrams: subclasses should not worry about
# ngrams. The base class will assemble ngrams if needed.


from abc import ABCMeta, abstractmethod
import itertools
import operator
from pprint import pprint

import testable


class Tzer(object, metaclass=ABCMeta):
   def __init__(self, ngram):
      if (ngram < 1):
         raise ValueError('ngram must be >= 1, but %d given' % (ngram))
      self.ngram = ngram

   def __str__(self):
      return '%s.%s;%d' % (self.__class__.__module__, self.__class__.__name__,
                           self.ngram)

   def tokenize(self, s):
      if (s is None):
         return []
      elif (isinstance(s, str)):
         # The basic approach here:
         # 1. Find the unigram sequence u and copy this to the output.
         # 2. Bigrams: append itertools.izip(u, u[1:])
         # 3. Trigrams: append itertools.izip(u, u[1:], u[2:])
         # 4. etc.
         unigrams = self.tokenize_real(s)
         tokens = list(unigrams)
         sources = [unigrams]
         for i in range(1, self.ngram):
            sources.append(unigrams[i:])
            tokens += (' '.join(j) for j in zip(*sources))
         return tokens
      else:
         raise TypeError('expected unicode or None, got %s' % (type(s)))

   def tokenize_all(self, dict_):
      '''Given a dictionary of strings, tokenize each string separately, then
         return a sequence of (key, token) pairs. For example:

         >>> t = Whitespace(1)
         >>> sorted(t.tokenize_all({ 'a': 'b c', \
                                     'd': 'e f g!' }))
         [('a', 'b'), ('a', 'c'), ('d', 'e'), ('d', 'f'), ('d', 'g!')]'''
      result = []
      for (key, s) in dict_.items():
         tokens = self.tokenize(s)
         result += [(key, i) for i in tokens]
      return result

   @abstractmethod
   def tokenize_real(self, s):
      '''Given a unicode s, tokenize it and return the tokenization as a
         sequence of tokens. s is guaranteed to be a unicode object.'''


class Whitespace(Tzer):
   'Just split on whitespace and squash case.'

   def tokenize_real(self, text):
      return text.lower().split()


# These are some strings good for testing.
T_CH = '美加緊'  # Kanji
T_EN = "Fox didn't jump over dog."
T_EN_TOKS = ['fox', 'didn', 't', 'jump', 'over', 'dog']
T_EN_TOKS_ICU = ['fox', "didn't", 'jump', 'over', 'dog']
T_EN_TOKS_PUNC = ['fox', 'didn', "'", 't', 'jump', 'over', 'dog', '.']
T_EN_TOKS_PUNC_ICU = ['fox', "didn't", 'jump', 'over', 'dog', '.']
T_FR = 'Français est amusant'
T_FR_TOKS = ['français', 'est', 'amusant']
T_JP2 = '私の'
# Example from TinySegmenter documentation: "My name is Nakano"
T_JP = '私の名前は中野です'
T_JP_TOKS = ['私', 'の', '名前',
             'は', '中野',
             'です']
T_KO = '갰'
T_PUNCT = '!@#$%^&*(_+-=[]{}\|;,.<>/?'
T_PUNCT_TOKS = []
T_WEIRD = 'ℝ☺♀'  # math, emoji, etc.
T_WEIRD_TOKS = []

testable.register('''

# FIXME: I haven't figured out how to print the actual Unicode characters in
# order to test them in a natural way. For example, letting the doctest
# "shell" print a Unicode string gets you a heavily encoded string full of
# "\u79c1" escape sequences rather than the characters themselves (you can use
# print to make an individual string work, but that doesn't help for
# sequences). Hence all the tests against True rather than a list.

# Tokenizers should return the empty sequence in some cases
>>> Whitespace(1).tokenize(None)
[]
>>> Whitespace(1).tokenize('')
[]

# ngram <= 1 is an error
>>> Whitespace(0).tokenize(None)
Traceback (most recent call last):
   ...
ValueError: ngram must be >= 1, but 0 given

# Test ngrams
>>> Whitespace(1).tokenize('a b c')
['a', 'b', 'c']
>>> Whitespace(2).tokenize('a b c')
['a', 'b', 'c', 'a b', 'b c']
>>> Whitespace(3).tokenize('a b c')
['a', 'b', 'c', 'a b', 'b c', 'a b c']

''')

def test_interactive():

   # Timing tests. This makes shell calls because (a) the timeit module
   # doesn't offer the smart iteration count guessing to Python that it does
   # on the command line and (b) to avoid significant overhead (I tried), one
   # must pass strings, not callables, even in Python, and they don't get the
   # calling namespace. It is very annoying.

   import os

   def time_test(class_, strings):
      print(class_, '...')
      cmd = "python -m timeit --setup 'import tokenizers; tzer=tokenizers.%s(1)' 'tzer.tokenize(%s)'" % (class_.split()[0], " + \" \" + ".join(['tokenizers.' + s for s in strings]))
      #print cmd
      os.system(cmd)

   time_test('ICU (fr + en)', ['T_FR', 'T_EN'])
   time_test('Tiny (jp)', ['T_JP'])
   time_test('Tiny_ICU (fr + en)', ['T_FR', 'T_EN'])
   time_test('Tiny_ICU (jp + fr + en)', ['T_JP', 'T_FR', 'T_EN'])
   time_test('Unicode_Props_Tiny (fr + en)', ['T_FR', 'T_EN'])
   time_test('Unicode_Props_Tiny (jp + fr + en)', ['T_JP', 'T_FR', 'T_EN'])
   time_test('Whitespace (fr + en)', ['T_FR', 'T_EN'])
