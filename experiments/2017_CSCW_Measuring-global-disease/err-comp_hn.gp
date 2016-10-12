errfile = ARG1
call "./base.gp" "6in" "2.5in"

set title errfile
set key left top

set ylabel "incidence error" font fontbold
set xlabel "date" font fontbold

set xdata time
set format x timeoutfmt

set xrange ["2010-07-04":]
set yrange [-1:2]

plot 0 notitle with lines lc black, \
     errfile using 1:2 title "normalized prediction error" with @ls_model
