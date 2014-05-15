#!/bin/bash

# This experiment tests the time gap between training and testing.

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances 3 \
    --model geo.gmm.Token \
    --model-parms weight_f:wt_inv_error_sae \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --gap { P0D , P1D , P2D , P4D , P8D , P16D , P32D , P64D , P128D } \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
