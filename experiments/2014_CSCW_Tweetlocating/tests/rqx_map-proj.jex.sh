#!/bin/bash

# Does map projection have any effect?

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances 3 \
    --model geo.gmm.Token \
    --model-parms weight_f:wt_inv_error_sae \
    --srid { 4326 , 540036 , 540096 } \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
