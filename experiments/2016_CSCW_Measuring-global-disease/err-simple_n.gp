prfile_all = ARG1
prfile_first = ARG2
call "./base.gp" "6in" "2.5in"

stats prfile_all name "pr" nooutput

set title prfile_all

set key left top

set ylabel "incidence error" font fontbold
set xlabel "date" font fontbold

set xdata time
set format x timeoutfmt

set xrange ["2010-07-04":]
set yrange [-1:2]


plot NaN title "normalized prediction error" with @ls_model, \
     0 notitle with lines lc black, \
     for [i=2:pr_columns-1] prfile_all using 1:i notitle with @ls_model_t
