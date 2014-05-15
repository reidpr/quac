#!/bin/bash

# This experiment tests different values of the covariance_type and min_covar
# parameters for GMM fitting.

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances 3 \
    --model geo.gmm.Token \
    --model-parms weight_f:sae_opt \
      { covariance_type:spherical , \
        covariance_type:tied , \
        covariance_type:diag , \
        covariance_type:full } \
      { min_covar:0.001 , \
        min_covar:0.002 , \
        min_covar:0.004 , \
        min_covar:0.008 , \
        min_covar:0.016 , \
        min_covar:0.032 , \
        min_covar:0.064 , \
        min_covar:0.128 , \
        min_covar:0.256 , \
        min_covar:0.512 , \
        min_covar:1.0 } \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --gap P0D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
