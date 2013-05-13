set terminal pdfcairo enhanced rounded size 5in,3.5in
font_ = "Helvetica Bold"

set xlabel "date" font font_
set timefmt "%Y-%m-%d"
set xdata time
set format x "%y-%b"

set ylabel "number of tweets collected" font font_
set yrange [0:]
set format y "%.1s %c"

# Double inversion is a trick to get NaN (and thus a gap in the graph) if
# there were no data on a given day.
plot "/dev/stdin" using 1:(1/(1/$2)) \
  notitle \
  with lines lt 4 lw 3 lc rgb "blue"
