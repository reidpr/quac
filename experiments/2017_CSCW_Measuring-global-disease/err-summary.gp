errfile = ARG1
call "./base.gp" "6in" "2.5in"

set title errfile

set ylabel "normalized absolute incidence error" font fontbold
#set yrange [0:2]
set logscale y

set bmargin 3  # make room for 2-line labels

plot errfile using 0:2:6 notitle with @fc_err_full, \
     errfile using 0:3:5 notitle with @fc_err_some, \
     errfile using 0:4:xtic(7) title "median" with @ls_err_mid, \
     errfile using 0:3 title "central 90%" with @ls_err_some, \
     errfile using 0:2 title "central 98%" with @ls_err_full, \
     errfile using 0:5 notitle with @ls_err_some, \
     errfile using 0:6 notitle with @ls_err_full, \
