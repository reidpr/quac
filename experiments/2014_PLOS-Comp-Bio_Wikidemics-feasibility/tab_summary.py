#!/usr/bin/env python

"""
	Generate LaTeX table summaries of our results for the paper.
"""

# Copyright (c) Los Alamos National Security, LLC and others.

import sys
import xlrd

print r'''
\begin{tabular}{|ll|l|rrrr|rr|}
\hline

&
&
& \multicolumn{4}{c|}{\textbf{$\boldsymbol{r^2}$ at forecast}}
& \multicolumn{2}{c|}{\textbf{Best forec.}}
\\
  \multicolumn{1}{|c}{\textbf{Disease}}
& \multicolumn{1}{c}{\textbf{Location}}
& \multicolumn{1}{|c|}{\textbf{Result}}
& \multicolumn{1}{c}{\textbf{0}}
& \multicolumn{1}{c}{\textbf{7}}
& \multicolumn{1}{c}{\textbf{14}}
& \multicolumn{1}{c|}{\textbf{28}}
& \multicolumn{1}{c}{\textbf{Days}}
& \multicolumn{1}{c|}{$\boldsymbol{r^2}$}
\\
'''

book = xlrd.open_workbook(sys.argv[1])
sh = book.sheet_by_index(0)

last_disease = None
for ri in xrange(2, sh.nrows):
   v = sh.row_values(ri)
   if (v[0]):  # ppr?
      disease = v[1]
      if (disease != last_disease):
         print r'\hline'
         disease_pr = disease
      else:
         disease_pr = ''
      print r' & '.join((disease_pr,
                         v[3],             # location
                         v[8],             # result
                         '%.2f' %  v[15],  # r^2 at nowcast
                         '%.2f' %  v[14],  # r^2 at 7-day forecast
                         '%.2f' %  v[13],  # r^2 at 14-day forecast
                         '%.2f' %  v[11],  # r^2 at 28-day forecast
                         '%d'   % -v[10],  # best offset
                         '%.2f' %  v[9],   # max(r^2)
                       )),
      print r'\\'
      last_disease = disease

print r'''
\hline
\end{tabular}
'''
