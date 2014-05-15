#!/bin/bash

# Some estimators have problems with SRID 4326. This script demonstrates the
# problem: success_ct is 0 (or almost), when it should be 100 (or almost).

. $(dirname $0)/parseargs.sh

model-test \
    --min-instances 10 \
    --srid 4326 \
    --model geo.gmm.Token \
    --model-parms weight_feature:aic \
    --test-tweet-limit 100 \
    --start 2012-03-20T07:00:00+00:00 \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --cores $CORE_CT \
    --limit 1 \
    --verbose \
    $GEODB $JOBDIR |& tee $JOBDIR/out
