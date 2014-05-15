#!/bin/bash

# This experiment mainly tests timing: how much training data is needed, and
# how long can we wait between the training set and the testing set.

echo 'needs update to use parseargs.sh'
exit 1

set -x

jexplode $2 $3 \
model-test \
    --model geo.gmm.Token \
    --model-parms { weight_f:sae_opt , \
                    weight_f:wt_inv_feature weight_feature:covar_sumprod } \
    --start 2012-02-01 \
    --end 2012-11-01 \
    --training { PT90M , PT3H , PT6H , PT12H , P1D , P2D , P4D } \
    --testing P1D \
    --stride P13D \
    --gap { P0D , P1D , P2D , P4D , P8D , P16D , P32D , P64D , P128D } \
    --cores $3 \
    --verbose \
    $1 $2/@id
