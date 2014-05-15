#!/bin/bash

# A quick sanity check to make sure model-test runs to completion.

# Note: When run on the april1-7 database, this will produce a nonattempted
# test due to lack of data. This is by design.... :)

. $(dirname $0)/parseargs.sh

model-test \
    --model geo.gmm.Token \
    --model-parms weight_f:wt_inv_feature weight_feature:covar_sumprod \
    --test-tweet-limit 500 \
    --start 2012-04-01 \
    --training P1D \
    --testing P1D \
    --cores $CORE_CT \
    --limit 1 \
    --verbose \
    $GEODB $JOBDIR |& tee $JOBDIR/out
