# Copyright (c) Los Alamos National Security, LLC, and others.

set terminal pdfcairo enhanced rounded size 5in,3.5in
font_ = "Helvetica Bold"

set xlabel "date" font font_
set timefmt "%Y-%m-%d"
set xdata time
set format x "%y-%b" #"%b%d"

set ylabel "fraction of tweets with geotag" font font_
set yrange [0:]
set format y "%.1f%%"

plot "/dev/stdin" using 1:(100*($3/$2)) \
  notitle \
  with lines lt 4 lw 3 lc rgb "blue" \
