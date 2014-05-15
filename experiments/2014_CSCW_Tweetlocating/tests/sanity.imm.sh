#!/bin/bash

# A quick sanity check to make sure model-test runs to completion.

# Note: When run on the april1-7 database, this will produce a nonattempted
# test due to lack of data. This is by design.... :)

. $(dirname $0)/parseargs.sh

model-test \
    --trim-head 0.02 \
    --model geo.gmm.Token \
    --test-tweet-limit 10 \
    --start 2012-03-31 \
    --training PT1H \
    --testing PT5M \
    --stride P2D \
    --cores $CORE_CT \
    --limit 2 \
    --random-seed 0 \
    --verbose \
    $GEODB $JOBDIR |& tee $JOBDIR/out
