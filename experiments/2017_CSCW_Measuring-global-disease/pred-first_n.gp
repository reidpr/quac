TRUTHFILE = ARG1
PRFILE_FIRST = ARG2
call "./base.gp" "6in" "2.5in"

#STALE_MAX = 7

stats PRFILE_FIRST name "pr" nooutput

set title PRFILE_FIRST

set key left top

set ylabel "incidence" font fontbold
set xlabel "date" font fontbold

set xdata time
set format x timeoutfmt

set yrange [0:]

do for [I=3:pr_columns] {
STALE = I - 3
plot TRUTHFILE using 1:(1.5*$2) notitle with @ls_trans, \
     TRUTHFILE using 1:2 noautoscale title "true incidence" with @ls_truth, \
     PRFILE_FIRST using 2:I noautoscale title sprintf("staleness %d", STALE) with @ls_model
}
