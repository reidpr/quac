#!/bin/bash

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

# We need a SLURM allocation with at least 2 nodes.
test "$SLURM_NODELIST" != "" && test "$SLURM_JOB_NUM_NODES" -ge 2
