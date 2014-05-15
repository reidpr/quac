#!/bin/bash

# This experiment tests various model settings on the Eisenstein et al data.

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --model geo.gmm.Token \
    --model-parms \
    { weight_f:wt_inv_error_sae wt_inv_error_exponent:1.0 , \
      weight_f:wt_inv_error_sae wt_inv_error_exponent:2.0 , \
      weight_f:wt_inv_error_sae wt_inv_error_exponent:4.0 , \
      weight_f:wt_inv_error_sae wt_inv_error_exponent:6.0 , \
      weight_f:wt_inv_error_sae wt_inv_error_exponent:8.0 , \
      weight_f:wt_inv_error_sae wt_inv_error_exponent:10.0 , \
      weight_f:wt_inv_error_sae wt_inv_error_exponent:12.0 , \
      weight_f:wt_inv_error_sae wt_inv_error_exponent:14.0 , \
      weight_f:wt_inv_error_sae wt_inv_error_exponent:16.0 , \
      weight_f:sae_opt opt_feature_id:1 opt_feature_misc:0 , } \
    --fields tx \
    --tokenizer tok.base.Whitespace \
    --ngram 1 \
    --min-instances 1 \
    --start 2012-01-01 \
    --end 2012-01-05 \
    --training P2D \
    --testing P1D \
    --stride P1D \
    --gap P0D \
    --limit 1 \
    --cores $CORE_CT \
    --skip-small-tests 0 \
    --verbose \
    $GEODB $JOBDIR/@id
