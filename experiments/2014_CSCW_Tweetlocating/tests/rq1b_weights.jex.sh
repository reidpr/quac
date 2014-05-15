#!/bin/bash

# This experiment tests which way of GMM weighting during combine() is best.

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances 3 \
    { --model geo.gmm.All_Tweets , \
      --model geo.gmm.Token --model-parms weight_f:sae_opt opt_feature_id:1 opt_feature_misc:0 , \
      --model geo.gmm.Token --model-parms weight_f:sae_opt opt_feature_id:0 opt_feature_misc:1 , \
      --model geo.gmm.Token --model-parms weight_f:sae_opt opt_feature_id:1 opt_feature_misc:1 , \
      --model geo.gmm.Token --model-parms weight_f:sae_opt component_ct_max:1 opt_feature_id:1 opt_feature_misc:0 , \
      --model geo.gmm.Token --model-parms weight_f:sae_opt component_ct_max:1 opt_feature_id:0 opt_feature_misc:1 , \
      --model geo.gmm.Token --model-parms weight_f:sae_opt component_ct_max:1 opt_feature_id:1 opt_feature_misc:1 , \
      --model geo.gmm.Token --model-parms weight_f:wt_inv_feature weight_feature:one , \
      --model geo.gmm.Token --model-parms weight_f:wt_neg_feature weight_feature:aic , \
      --model geo.gmm.Token --model-parms weight_f:wt_inv_feature weight_feature:covar_sumprod , \
      --model geo.gmm.Token --model-parms weight_f:wt_inv_error_sae wt_inv_error_exponent:2.0 , \
      --model geo.gmm.Token --model-parms weight_f:wt_inv_error_sae wt_inv_error_exponent:4.0 , \
      --model geo.gmm.Token --model-parms weight_f:wt_inv_error_sae wt_inv_error_exponent:10.0 , \
      --model geo.gmm.Token --model-parms weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:2.0 , \
      --model geo.gmm.Token --model-parms weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:4.0 , \
      --model geo.gmm.Token --model-parms weight_f:wt_inv_error_cae wt_inv_sample_ct:50 wt_inv_error_exponent:10.0 } \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --gap P0D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
