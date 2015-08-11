#!/bin/bash

# Copyright (c) Los Alamos National Security, LLC, and others.

set -e
$(dirname $0)/../ready.sh

# We need a SLURM allocation with at least 2 nodes and MPI.
   test "$SLURM_NODELIST" != "" \
&& test "$SLURM_JOB_NUM_NODES" -ge 2 \
&& type mpirun > /dev/null
