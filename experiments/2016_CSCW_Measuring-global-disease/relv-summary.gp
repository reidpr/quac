datafile = ARG1
call "base.gp" "4in" "2.5in"

set xlabel "training period (weeks)"
set ylabel "fraction of articles"

#set grid ytics
set xtics scale 0

set style data histograms
set style histogram errorbars gap 1
set boxwidth 0.9
set style fill solid noborder

#set key left top

set yrange [0:1]

plot datafile using "relv_50":"relv_min":"relv_max":xtic(1) \
              title "relevant" ls -1 lc @q_set1_brown, \
     datafile using "appr_50":"appr_min":"appr_max":xtic(1) \
              title "relevant and English" ls -1 lc @q_set1_blue
