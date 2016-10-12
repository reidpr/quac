fontsize = 10
fontrm = "Bitstream Charter"
fontbold = fontrm." Bold"

timeoutfmt = "%Y"

# Default line width (i.e., lw=1 in plots) is 1/4 point, which seems to be
# roughly the minimum available.
set terminal pdfcairo font fontrm.",".fontsize enhanced rounded size @ARG1,@ARG2
set datafile separator "\t"
set timefmt "%Y-%m-%d"

# http://colorbrewer2.org/?type=qualitative&scheme=Set1&n=8
q_set1_red     = "rgb \"#e41a1c\""
q_set1_blue    = "rgb \"#377eb8\""
q_set1_green   = "rgb \"#4daf4a\""
q_set1_purple  = "rgb \"#984ea3\""
q_set1_orange  = "rgb \"#ff7f00\""
q_set1_yellow  = "rgb \"#ffff33\""
q_set1_brown   = "rgb \"#a65628\""
q_set1_brown_t = "rgb \"#d0a65628\""
q_set1_pink    = "rgb \"#f781bf\""

ls_trans = "lines lc rgb \"#ff000000\""
ls_truth = "lines lw 2 lc @q_set1_blue"
ls_model = "lines lw 2 lc @q_set1_brown"
ls_model_t = "lines lw 1 lc rgb\"#70a65628\""
ps_model = "points pt 13 ps 0.2 lc @q_set1_brown"

ls_err_mid = "lines lw 2.5 lc @q_set1_brown"
ls_err_some = "lines dt 2 lw 1 lc @q_set1_brown"
fc_err_some = "filledcurves lc @q_set1_brown_t"
ls_err_full = "lines dt 3 lw 1 lc @q_set1_brown"
fc_err_full = "filledcurves lc @q_set1_brown_t"
