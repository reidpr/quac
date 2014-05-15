#!/bin/bash

# Does removing popular tokens have any effect?

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --trim-head { 0 , \
                  0.000001 , \
                  0.000002 , \
                  0.000004 , \
                  0.000008 , \
                  0.000016 , \
                  0.000032 , \
                  0.000064 , \
                  0.000128 , \
                  0.000256 , \
                  0.000512 , \
                  0.001024 , \
                  0.002048 , \
                  0.004096 , \
                  0.008192 , \
                  0.016384 , \
                  0.032768 , \
                  0.065536 , \
                  0.131072 , \
                  0.262144 } \
    --min-instances 3 \
    --model geo.gmm.Token \
    --model-parms weight_f:wt_inv_error_sae \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
