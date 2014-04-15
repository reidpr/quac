#!/usr/bin/env python

# This script creates a copy of Selections.xls, Selections+r.xls, with the
# correlation values filled in for creating the table in the paper. You must
# copy and paste the r values back into Selections.xls, as the formulas get
# trashed by the translation.
#
# It must be run with CWD containing Selections.xls
#
# NOTE: This script is quick and dirty. I'm not proud.

# Copyright (c) Los Alamos National Security, LLC and others.

from collections import defaultdict
import glob
from pprint import pprint

import xlrd
import xlutils.copy
import xlwt

INFILE='Selections.xls'
OUTFILE='Selections+r.xls'
corrs=dict()

def corr(disease, lang, url):
   try:
      cs = corrs[disease][lang]
   except KeyError:
      corrs[disease] = dict()
      corrs[disease][lang] = dict()
      cs = corrs[disease][lang]
      glob_ = '../regression_results/%s_%s_*_M.txt' % (lang, disease)
      #print 'glob is %s' % (glob_)
      file_ = glob.glob(glob_)
      if (len(file_) == 0):
         #print 'no file found'
         pass
      else:
         file_ = file_[0]
         #print 'reading correlations from %s' % (file_)
         with open(glob.glob(file_)[0]) as fp:
            for line in fp:
               splits = line.split()
               if (len(splits) >= 1 and splits[0] == lang):
                  corrs[disease][lang][splits[2]] = float(splits[5])
   try:
      return cs[url]
   except KeyError:
      return None

print 'loading old version'
rbook = xlrd.open_workbook(INFILE, formatting_info=True)

# We do this loop a second time before the copy because sometimes the copy
# takes a very long time because all the cells have been instantiated for some
# reason. Gnumeric does this sometimes. If it happens, save the file with
# LibreOffice and you are OK.
for (si, sn) in enumerate(rbook.sheet_names()):
   rsheet = rbook.sheet_by_index(si)
   print ('found sheet %d: %s (%d rows, %d cols)'
          % (si, sn, rsheet.nrows, rsheet.ncols))

print 'making writeable copy'
wbook = xlutils.copy.copy(rbook)

print 'processing'
for (si, disease) in enumerate(rbook.sheet_names()):
   rsheet = rbook.sheet_by_index(si)
   wsheet = wbook.get_sheet(si)
   print ('found sheet %d: %s (%d rows, %d cols)'
          % (si, disease, rsheet.nrows, rsheet.ncols))
   for lang_ci in xrange(0, rsheet.ncols, 3):
      lang = rsheet.cell_value(0, lang_ci)
      print 'checking column %d: found language "%s"' % (lang_ci, lang)
      if (lang == ''):
         print 'no more languages; stopping'
         break
      url_ci = lang_ci + 1
      r_ci = lang_ci + 2
      for ri in xrange(1, rsheet.nrows):
         url = rsheet.cell_value(ri, url_ci)[29:]
         if (url != ''):
            r = corr(disease, lang, url)
            #print 'found at row %2d article %s; r = %s' % (ri, url, r)
            wsheet.write(ri, r_ci, r)

print 'saving'
wbook.save(OUTFILE)

print 'NOTE: Now you need to copy the r values back into Selections.xls!'
