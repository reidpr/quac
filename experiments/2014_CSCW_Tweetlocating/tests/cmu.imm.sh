#!/bin/bash

# CMU data experiment. DB is at $GUNNISION:~culotta/db.cmu

echo 'needs update to use parseargs.sh'
exit 1

set -x

model-test \
    --model "geo.gmm.Token" \
    --model-parms gmm_fit_f:gmm_fit_log_heuristic weight_f:cae_opt \
    --fields tx \
    --ngram 1 \
    --tokenizer tokenizers.Whitespace \
    --start 2012-01-01 \
    --end 2012-01-05 \
    --training PT2D \
    --testing PT1D \
    --gap P0D \
    --stride P1D \
    --limit 1 \
    --verbose \
    $1 $2
