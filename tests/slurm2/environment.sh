# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

. ../environment.sh

# the two nodes we've been allocated
export SLURM_NODE_A=$(scontrol show hostname | head -1 | tail -1)
export SLURM_NODE_B=$(scontrol show hostname | head -2 | tail -1)
