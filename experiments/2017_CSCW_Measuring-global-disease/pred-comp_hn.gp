truthfile = ARG1
prfile = ARG2
call "./base.gp" "6in" "2.5in"

set title prfile
set key left top

set ylabel "incidence" font fontbold
set xlabel "date" font fontbold

set xdata time
set format x timeoutfmt

set yrange [0:]

plot truthfile using 1:(1.5*$2) notitle with @ls_trans, \
     truthfile using 1:2 noautoscale title "true incidence" with @ls_truth, \
     prfile using 1:2 noautoscale title "predictions" with @ls_model
