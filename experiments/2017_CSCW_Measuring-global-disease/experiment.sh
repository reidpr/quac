#!/bin/bash

if [[ $# -lt 3 ]]; then
   echo fail
   exit 1
fi

set -e
#set -x

INDIR=$1
#OUTDIR=$2/f.$(date '+%Y-%m-%d_%H.%M.%S')
OUTDIR=$2
WHAT=$3
SENTINEL=$OUTDIR/spatula_city

if [[ -d $OUTDIR ]]; then
     if [[ -f $SENTINEL ]]; then
         rm -Rf $OUTDIR
     else
         echo "$OUTDIR exists but doesn't seem to be experiment output"
         exit 1
     fi
fi
mkdir $OUTDIR
touch $SENTINEL

cd $(dirname $0)

export PYTHONUNBUFFERED=1

# FIXME: pipe just stderr

TESTSTRIDE=1
HORIZONS='0 1 2 3 4 6 8 12 16'
TRAININGS='16 26 39 52 78 104 130'

if [[ $WHAT == 'test' ]]; then
    ./experiment.py \
        --in $INDIR \
        --out $OUTDIR \
        --outbreaks us+influenza \
        --distance 3 \
        --teststride $TESTSTRIDE \
        --horizons 0 2 \
        --trainings 16 52 \
        2>&1 | tee $OUTDIR/log
elif [[ $WHAT == 'flu' ]]; then
    for DIST in 1 2 3 4 5 6 7 8; do
        REAL_OUT=$OUTDIR/d$DIST
        mkdir $REAL_OUT
        ./experiment.py \
            --in $INDIR \
            --out $REAL_OUT \
            --outbreaks us+influenza xx+influenza \
            --distance $DIST \
            --teststride $TESTSTRIDE \
            --horizons $HORIZONS \
            --trainings $TRAININGS \
            2>&1 | tee $REAL_OUT/log
    done
elif [[ $WHAT == 'global' ]]; then
    for DIST in 2 3; do
        REAL_OUT=$OUTDIR/d$DIST
        mkdir $REAL_OUT
        ./experiment.py \
            --in $INDIR \
            --out $REAL_OUT \
            --distance $DIST \
            --teststride $TESTSTRIDE \
            --horizons $HORIZONS \
            --trainings $TRAININGS \
            2>&1 | tee $REAL_OUT/log
    done
fi
