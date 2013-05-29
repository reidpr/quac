#!/bin/sh

# Wrapper script to run a parsing make job in a particular directory and drop
# a lock directory, to avoid multiple makes working in the same directory at
# the same time.

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

set -e  # stop script on error
#set -x  # echo commands

cores=$1
cd $2
lockdir=parse.lock
make="make -j $cores -f $(dirname $0)/parse.mk"

# Clean up the lockdir no matter how we exit. (Note: if a parallel make is
# interrupted, this will execute multiple times, but that's OK.)
trap "rmdir $lockdir || true" INT TERM EXIT

if (! mkdir $lockdir); then
    echo 'could not acquire lock; is another parse running?' 1>&2
    exit 1
else
    $make all
    # FIXME: missing rawtsv files leads to one extra day of .raw.tsv being
    # rebuilt per make run. WTF?
    #$make clean-rawtsv
fi

