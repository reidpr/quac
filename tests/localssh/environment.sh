# Copyright (c) Los Alamos National Security, LLC, and others.

. ../environment.sh

# We want to use localhost even if running in a SLURM allocation.
unset SLURM_NODELIST
