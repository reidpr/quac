# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

set terminal pdfcairo enhanced rounded size 5in,1.5in
font_ = "Helvetica Bold"

set xlabel "date" font font_
set timefmt "%Y-%m-%d"
set xdata time
set format x "%y-%b"

set ylabel "good data" font font_
set yrange [-0.5:1.5]
set ytics ( 'no' 0, 'yes' 1 )

validdata(x) = x >= 100000 ? 1 : 0

plot "/dev/stdin" using 1:(validdata($2)) \
  notitle \
  with points lt 0 lc rgb "blue"
