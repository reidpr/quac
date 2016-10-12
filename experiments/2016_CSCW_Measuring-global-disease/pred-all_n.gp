truthfile = ARG1
prfile_all = ARG2
prfile_first = ARG3
call "./base.gp" "6in" "2.5in"

stats prfile_all name "pr" nooutput

set title prfile_all

set key left top

set ylabel "incidence" font fontbold
set xlabel "date" font fontbold

set xdata time
set format x timeoutfmt

set yrange [0:]

plot truthfile using 1:(1.5*$2) notitle with @ls_trans, \
     truthfile using 1:2 noautoscale title "true incidence" with @ls_truth, \
     NaN title "predictions" with @ls_model, \
     for [i=2:pr_columns-1] prfile_all using 1:i noautoscale notitle with @ls_model_t

do for [i=2:pr_columns-1] {
plot truthfile using 1:(1.5*$2) notitle with @ls_trans, \
     truthfile using 1:2 noautoscale title "true incidence" with @ls_truth, \
     prfile_all using 1:i noautoscale title sprintf("prediction %d", i) with @ls_model
}
