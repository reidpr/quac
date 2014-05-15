#!/bin/bash

# Effect of component_sz_min

. $(dirname $0)/parseargs.sh

jexplode $JOBDIR $CORE_CT \
model-test \
    --min-instances 3 \
    --model geo.gmm.Token \
    --model-parms weight_f:sae_opt { component_sz_min:1 , \
                                     component_sz_min:2 , \
                                     component_sz_min:3 } \
    --start $START \
    --end $END \
    --training P1D \
    --testing P1D \
    --stride P6D \
    --gap P0D \
    --cores $CORE_CT \
    --verbose \
    $GEODB $JOBDIR/@id
