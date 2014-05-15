#!/bin/bash

# Which parameters of wt_inv_error are best? How does it compare to the other
# leaders?

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances 3 \
    --model geo.gmm.Token \
    --model-parms \
      { weight_f:wt_inv_feature , \
        weight_f:sae_opt , \
        weight_f:wt_inv_error_sae wt_inv_error_exponent:2.0  , \
        weight_f:wt_inv_error_sae wt_inv_error_exponent:3.0  , \
        weight_f:wt_inv_error_sae wt_inv_error_exponent:4.0  , \
        weight_f:wt_inv_error_sae wt_inv_error_exponent:5.0  , \
        weight_f:wt_inv_error_sae wt_inv_error_exponent:6.0  , \
        weight_f:wt_inv_error_sae wt_inv_error_exponent:8.0  , \
        weight_f:wt_inv_error_sae wt_inv_error_exponent:10.0 , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:25 wt_inv_error_exponent:2.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:25 wt_inv_error_exponent:3.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:25 wt_inv_error_exponent:4.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:25 wt_inv_error_exponent:5.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:25 wt_inv_error_exponent:6.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:25 wt_inv_error_exponent:8.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:25 wt_inv_error_exponent:10.0 , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:2.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:3.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:4.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:5.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:6.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:8.0  , \
        weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:10.0 } \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --gap P0D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
