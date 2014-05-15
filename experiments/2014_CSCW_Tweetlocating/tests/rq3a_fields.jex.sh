#!/bin/bash

# This experiment tests which fields contain useful location information.

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances 3 \
    --model geo.gmm.Token \
    --model-parms weight_f:wt_inv_error_sae \
    --fields { tx } { ds } { ln } { lo } { tz } \
    --unify-fields { 0 , 1 } \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
