#!/bin/bash

# Does removing unpopular tokens have any effect?

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances { 2 , 3 , 4 , 5 , 6 , 8 , 10 , 12 , 14 , 20 , 28 , 40 } \
    --model geo.gmm.Token \
    --model-parms weight_f:wt_inv_error_sae wt_inv_min_tweets:2 \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
