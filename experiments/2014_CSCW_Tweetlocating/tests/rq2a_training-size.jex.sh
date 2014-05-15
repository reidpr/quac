#!/bin/bash

# This experiment tests how much training data is needed.

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances 3 \
    --model geo.gmm.Token \
    --model-parms weight_f:wt_inv_error_sae \
    --start $START \
    --end $END \
    --training { PT90M , PT3H , PT6H , PT12H , P1D , P2D , P4D , P8D , P16D } \
    --testing P1D \
    --stride P13D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
