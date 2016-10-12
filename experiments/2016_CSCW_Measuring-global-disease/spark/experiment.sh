#!/bin/bash

# Run the experiment, dealing with all the PySpark fun

# Why Spark is a pain
#
#   - pyfiles ships files AND imports them
#
#   - imports from driver program don't stick
#
#   - standard Java stacktrace explosions for a one-line error
#
#   - can't reference classes that use slots because CloudPickle goes into
#     infinite recursion
#
#   - tendency for strange errors, e.g. "RuntimeError: uninitialized
#     classmethod object" has essentially no google results
#
#   - can't call class methods or static methods
#
#   - can't use classes from the main module
#     (https://issues.apache.org/jira/browse/SPARK-3321,
#     http://stackoverflow.com/questions/28569374/)
#
#   - Functions don't happen when they're called via SparkContext; they happen
#     later. Thus, logging may be misleading.
#
#   - excessive imports in inner loop? see https://mail-archives.apache.org/mod_mbox/spark-user/201509.mbox/%3CF58C8F58-D6F3-45ED-B176-C07D9BFB63F9%40lanl.gov%3E
#
#   - import issues don't seem to be unique to Spark. E.g., here's a basic
#     implementation called mincemeat, and it requires you to re-import in all
#     the functions: <https://github.com/ziyuang/mincemeatpy>. Disco is the
#     same way.

# Pandas gotchas
#
#   - week aliases e.g. W-SAT refer to the *end* of the week, e.g W-SAT means
#     "weeks, ending on Saturday". See
#     http://github.com/pydata/pandas/blob/master/pandas/tseries/frequencies.py
#     lines 618-624. This goes for the other period codes as well, e.g. A-DEC
#     means "annual, december year end". point being if you want MMWR weeks
#     starting on Sunday, then the proper alias is W-SAT.

# Notes
#
#   - Assume a 1-period lag on truth. That is, for a forecast horizon of zero,
#     we train on data up to now minus one period.

set -e
set -x

OUTDIR=/data/f.$(date '+%Y-%m-%d_%H.%M.%S')
rm -Rf $OUTDIR
mkdir $OUTDIR

cd $(dirname $0)

#mpirun -n 1 ./experiment-mpi \
/usr/local/spark/bin/spark-submit \
    --master local[4] \
    experiment.py \
    --candidates 50 \
    --freq W-SAT \
    --teststride 4 \
    /data/wp-flu/ts2 \
    ~/forecasting-paper/truth.xlsx \
    $OUTDIR \
    --horizon 0 1 2 4 6 8 12 16 24 \
    --training 52 78 104 130 156 182 208
#    --horizon 0 \

for i in $(find $OUTDIR -name '*.prof' -o -name '*.pstats'); do
    gprof2dot -f pstats -n 1 $i | dot -Tpdf -o $i.pdf
done
