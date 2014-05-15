#!/bin/bash

# Small experiment to profile optimize.py

echo 'needs update to use parseargs.sh'
exit 1

set -x

model-test \
    --model "geo.gmm.Token" \
    --model-parms gmm_fit_f:gmm_fit_log_heuristic weight_f:cae_opt \
    --test-tweet-limit 100 \
    --start 2012-04-02 \
    --end 2012-04-08 \
    --training PT1H \
    --testing PT3H \
    --gap P4D \
    --stride P1D \
    --limit 1 \
    --verbose \
    $1 $2
