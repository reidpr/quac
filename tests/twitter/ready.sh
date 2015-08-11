#!/bin/bash

# Copyright (c) Los Alamos National Security, LLC, and others.

set -e
$(dirname $0)/../ready.sh

test -e $(dirname $0)/tweets/raw/big/big.json.gz
